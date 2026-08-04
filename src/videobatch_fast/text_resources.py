from __future__ import annotations

import ast
import string
from functools import lru_cache
from pathlib import Path
from typing import Any

from .registry import PROJECT_ROOT, RegistryError, load_json

RESOURCE_PATH = "resources/texts/de.json"
SUPPORTED_SCHEMA_VERSION = 2
SUPPORTED_CATALOG_VERSION = "1.0"
_VISIBLE_KEYWORDS = {"text", "title", "message", "label"}
_MESSAGEBOX_FUNCTIONS = {"showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askretrycancel"}


class TextResourceError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _catalog() -> dict[str, str]:
    manifest = load_json(RESOURCE_PATH)
    if manifest.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise TextResourceError("Textkatalog-Schema wird von dieser Programmversion nicht unterstützt.")
    version = str(manifest.get("catalog_version", ""))
    if version != SUPPORTED_CATALOG_VERSION:
        raise TextResourceError(f"Textkatalog-Version wird nicht unterstützt: {version or '-'}")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise TextResourceError("Textkatalog enthält keine Textdateien.")
    catalog: dict[str, str] = {}
    for filename in files:
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".json"):
            raise TextResourceError(f"Textkatalog-Dateiname ist ungültig: {filename}")
        part = load_json(f"resources/texts/{filename}")
        if part.get("catalog_version") != version or not isinstance(part.get("texts"), dict):
            raise TextResourceError(f"Textkatalog-Datei ist nicht kompatibel: {filename}")
        for key, value in part["texts"].items():
            if not isinstance(key, str) or not key.strip():
                raise TextResourceError(f"Textressource enthält einen ungültigen Schlüssel: {filename}")
            if key in catalog:
                raise TextResourceError(f"Textschlüssel ist doppelt: {key}")
            if not isinstance(value, str) or not value.strip():
                raise TextResourceError(f"Textressource ist leer oder ungültig: {key}")
            catalog[key] = value
    return catalog


def clear_text_cache() -> None:
    _catalog.cache_clear()
    from .registry import clear_registry_cache

    clear_registry_cache()


def text(key: str, fallback: str | None = None, /, **values: Any) -> str:
    """Return one UI text and fail visibly on missing release resources."""
    value = _catalog().get(key)
    if value is None:
        if fallback is not None:
            value = fallback
        else:
            raise TextResourceError(f"Textschlüssel fehlt: {key}")
    if not values:
        return value
    try:
        return value.format_map(values)
    except (KeyError, ValueError) as exc:
        raise TextResourceError(f"Textplatzhalter ungültig: {key}: {exc}") from exc


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _used_text_keys(source_root: Path) -> tuple[set[str], list[str]]:
    keys: set[str] = set()
    errors: list[str] = []
    for path in sorted(source_root.glob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            errors.append(f"Textprüfung kann {path.name} nicht analysieren: {exc}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "text" or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.add(first.value)
            else:
                # Dynamische Schlüssel sind für kleine, im Code definierte Schlüssellisten erlaubt.
                continue
    return keys, errors


def _raw_visible_literals(source_root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(source_root.glob("*.py")):
        if not (path.name.startswith("ui") or path.name in {"workflow_dialogs.py", "app.py", "slideshow_editor.py"}):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = _call_name(node)
            candidates: list[ast.AST] = []
            for keyword in node.keywords:
                if keyword.arg in _VISIBLE_KEYWORDS:
                    candidates.append(keyword.value)
                if function == "StringVar" and keyword.arg == "value":
                    candidates.append(keyword.value)
            if function in _MESSAGEBOX_FUNCTIONS:
                candidates.extend(node.args[:2])
            if function == "Tooltip" and len(node.args) >= 2:
                candidates.append(node.args[1])
            if function == "title" and node.args:
                candidates.append(node.args[0])
            for candidate in candidates:
                if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str) and candidate.value.strip():
                    errors.append(
                        f"{path.name}:{candidate.lineno}: sichtbarer Text ist nicht ausgelagert: {candidate.value[:60]!r}"
                    )
    return errors


def _validate_placeholders(key: str, value: str) -> list[str]:
    errors: list[str] = []
    try:
        fields = [field for _, field, _, _ in string.Formatter().parse(value) if field]
    except ValueError as exc:
        return [f"{key}: ungültige Platzhalter-Syntax: {exc}"]
    for field in fields:
        if not field.replace("_", "").isalnum():
            errors.append(f"{key}: unsicherer Platzhalter: {field}")
    return errors


def validate_text_resources(project_root: Path | None = None) -> list[str]:
    root = project_root or PROJECT_ROOT
    errors: list[str] = []
    try:
        catalog = _catalog()
    except (RegistryError, TextResourceError) as exc:
        return [str(exc)]
    used, parse_errors = _used_text_keys(root / "src" / "videobatch_fast")
    errors.extend(parse_errors)
    missing = sorted(used - set(catalog))
    if missing:
        errors.append("Textschlüssel fehlen: " + ", ".join(missing))
    errors.extend(_raw_visible_literals(root / "src" / "videobatch_fast"))
    for key, value in catalog.items():
        errors.extend(_validate_placeholders(key, value))
    return errors
