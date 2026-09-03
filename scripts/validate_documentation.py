#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = ROOT / "docs" / "DOCUMENTATION_CLASSIFICATION.json"
MANIFEST = ROOT / "RELEASE_MANIFEST.json"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
VERSION_RE = re.compile(r"(?<![\w.-])(\d+\.\d+\.\d+(?:-rc\d+)?)(?![\w.-])")
VERSION_LABEL_RE = re.compile(
    r"^\s*(?:[-*]\s*)?(?:\*\*|__)?(?:version|release[- ]?version|build[- ]?version)\s*[:=](?:\*\*|__)?\s*",
    re.IGNORECASE,
)
ALLOWED_CATEGORIES = frozenset({"active", "technical", "historical", "internal"})
STRICT_CATEGORIES = frozenset({"active", "technical"})
PRODUCT_VERSION_CONTEXT = (
    "videobatch",
    "videoautomation",
    "release candidate",
    "release-version",
    "releaseversion",
    "build-version",
    "buildversion",
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    message: str
    line: int | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            value["line"] = self.line
        return value


def load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} muss ein JSON-Objekt enthalten")
    return value


def current_version() -> str:
    manifest = load_json(MANIFEST)
    version = str(manifest.get("build") or manifest.get("version") or "").strip()
    if not version:
        raise ValueError("RELEASE_MANIFEST.json enthält keine Build- oder Versionsangabe")
    return version


def release_markdown_files() -> set[str]:
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from release_file_contract import included_release_file

    return {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.md")
        if included_release_file(ROOT, path)
    }


def strip_code_fences(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    in_fence = False
    marker = ""
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            token = stripped[:3]
            if not in_fence:
                in_fence = True
                marker = token
            elif token == marker:
                in_fence = False
                marker = ""
            cleaned.append("")
            continue
        cleaned.append("" if in_fence else line)
    return cleaned


def plain_heading(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"[*_~]", "", value)
    return " ".join(value.split()).strip()


def github_slug(value: str) -> str:
    text = plain_heading(value).casefold()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def headings(path: Path) -> list[tuple[int, str, str]]:
    result: list[tuple[int, str, str]] = []
    lines = strip_code_fences(path.read_text(encoding="utf-8").splitlines())
    for number, line in enumerate(lines, 1):
        match = HEADING_RE.match(line)
        if match:
            title = plain_heading(match.group(2))
            result.append((number, title, github_slug(title)))
    return result


def normalize_link_target(raw: str) -> str:
    target = raw.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target and not target.startswith("#"):
        target = target.split(" ", 1)[0]
    return unquote(target)


def validate_link(
    source: Path,
    raw_target: str,
    heading_cache: dict[Path, set[str]],
) -> str | None:
    target = normalize_link_target(raw_target)
    if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    if target.startswith("#"):
        anchor = target[1:]
        available = heading_cache.setdefault(
            source,
            {slug for _, _, slug in headings(source)},
        )
        return None if not anchor or anchor in available else f"Anker #{anchor} existiert in derselben Datei nicht"

    file_part, separator, anchor = target.partition("#")
    resolved = (source.parent / file_part).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return "Link verlässt den Repository-Stamm"
    if not resolved.is_file():
        return f"Zieldatei fehlt: {file_part}"
    if separator and anchor and resolved.suffix.lower() == ".md":
        available = heading_cache.setdefault(
            resolved,
            {slug for _, _, slug in headings(resolved)},
        )
        if anchor not in available:
            return f"Anker #{anchor} fehlt in {resolved.relative_to(ROOT).as_posix()}"
    return None


def product_series_prefix(version: str) -> str:
    base = version.split("-", 1)[0]
    parts = base.split(".")
    return ".".join(parts[:2]) + "." if len(parts) >= 2 else base


def stale_product_versions(text: str, version: str) -> list[tuple[str, int]]:
    """Return stale VideoBatch versions without mistaking tool versions for app versions."""
    series_prefix = product_series_prefix(version)
    findings: list[tuple[str, int]] = []
    for line_number, line in enumerate(strip_code_fences(text.splitlines()), 1):
        context = line.casefold()
        product_context = any(marker in context for marker in PRODUCT_VERSION_CONTEXT)
        product_context = product_context or bool(VERSION_LABEL_RE.search(line))
        for match in VERSION_RE.finditer(line):
            found = match.group(1)
            if found == version:
                continue
            if found.startswith(series_prefix) or product_context:
                findings.append((found, line_number))
    return findings


def validate() -> dict[str, Any]:
    findings: list[Finding] = []
    config = load_json(CLASSIFICATION)
    documents = config.get("documents")
    if not isinstance(documents, dict):
        raise ValueError("DOCUMENTATION_CLASSIFICATION.json benötigt ein Objekt 'documents'")

    actual = release_markdown_files()
    classified = set(map(str, documents))
    for path in sorted(actual - classified):
        findings.append(
            Finding(
                "DOC_UNCLASSIFIED",
                path,
                "Release-relevante Markdown-Datei ist nicht klassifiziert",
            )
        )
    for path in sorted(classified - actual):
        findings.append(
            Finding(
                "DOC_CLASSIFIED_MISSING",
                path,
                "Klassifizierte Markdown-Datei fehlt oder gehört nicht zum Release-Satz",
            )
        )

    version = current_version()
    heading_cache: dict[Path, set[str]] = {}
    checked_links = 0
    strictly_checked = 0

    for rel_path in sorted(actual & classified):
        entry = documents[rel_path]
        if not isinstance(entry, dict):
            findings.append(
                Finding(
                    "DOC_CLASSIFICATION_INVALID",
                    rel_path,
                    "Klassifikation muss ein JSON-Objekt sein",
                )
            )
            continue

        category = str(entry.get("category") or "")
        if category not in ALLOWED_CATEGORIES:
            findings.append(
                Finding(
                    "DOC_CATEGORY_INVALID",
                    rel_path,
                    f"Unbekannte Kategorie: {category!r}",
                )
            )
            continue

        # Historische Nachweise und interne Notizen werden nur auf Existenz und
        # Klassifikation geprüft. Ihre alten Überschriften, Links und Versionen
        # bleiben unverändert, damit der damalige Beweisstand nicht umgedeutet wird.
        if category not in STRICT_CATEGORIES:
            continue

        strictly_checked += 1
        path = ROOT / rel_path
        text = path.read_text(encoding="utf-8")
        doc_headings = headings(path)
        titles = {title.casefold() for _, title, _ in doc_headings}
        slugs: dict[str, int] = {}

        for line, title, slug in doc_headings:
            if not slug:
                findings.append(
                    Finding(
                        "DOC_EMPTY_HEADING_ANCHOR",
                        rel_path,
                        f"Überschrift erzeugt keinen stabilen Anker: {title}",
                        line,
                    )
                )
            elif slug in slugs:
                findings.append(
                    Finding(
                        "DOC_DUPLICATE_HEADING",
                        rel_path,
                        f"Überschrift erzeugt denselben Anker wie Zeile {slugs[slug]}: {title}",
                        line,
                    )
                )
            else:
                slugs[slug] = line

        if category == "active":
            required = entry.get("required_sections", [])
            if not isinstance(required, list) or not required:
                findings.append(
                    Finding(
                        "DOC_REQUIRED_SECTIONS_MISSING",
                        rel_path,
                        "Aktive Anleitung besitzt keine Pflichtabschnittsliste",
                    )
                )
            else:
                for section in required:
                    if str(section).casefold() not in titles:
                        findings.append(
                            Finding(
                                "DOC_REQUIRED_SECTION",
                                rel_path,
                                f"Pflichtabschnitt fehlt: {section}",
                            )
                        )

            for found, line in stale_product_versions(text, version):
                findings.append(
                    Finding(
                        "DOC_STALE_VERSION",
                        rel_path,
                        f"Veraltete Versionsangabe {found}; aktuell ist {version}",
                        line,
                    )
                )

        cleaned = "\n".join(strip_code_fences(text.splitlines()))
        for match in LINK_RE.finditer(cleaned):
            checked_links += 1
            problem = validate_link(path, match.group(1), heading_cache)
            if problem:
                line = cleaned.count("\n", 0, match.start()) + 1
                findings.append(
                    Finding(
                        "DOC_BROKEN_LINK",
                        rel_path,
                        problem,
                        line,
                    )
                )

    return {
        "schema_version": 1,
        "status": "passed" if not findings else "failed",
        "current_version": version,
        "classified_documents": len(classified),
        "release_markdown_documents": len(actual),
        "strictly_checked_documents": strictly_checked,
        "checked_links": checked_links,
        "findings": [finding.as_dict() for finding in findings],
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prüft den VideoBatch-Dokumentationsvertrag fail-closed."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Maschinenlesbares JSON ausgeben.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        report = validate()
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "status": "invalid",
            "findings": [
                {
                    "code": "DOC_VALIDATOR_INVALID",
                    "path": "",
                    "message": str(exc),
                }
            ],
        }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    elif report["status"] == "passed":
        print(
            "DOKUMENTATION BESTANDEN · "
            f"{report['release_markdown_documents']} klassifiziert · "
            f"{report['strictly_checked_documents']} streng geprüft · "
            f"{report['checked_links']} interne Links"
        )
    else:
        print("DOKUMENTATION FEHLERHAFT")
        for finding in report.get("findings", []):
            location = finding.get("path", "")
            if finding.get("line"):
                location += f":{finding['line']}"
            print(
                f"✕ {finding['code']} · {location} · {finding['message']}"
            )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
