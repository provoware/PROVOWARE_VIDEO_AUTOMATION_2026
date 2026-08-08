from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from .versioning import build_label

REPORT_NAME = "AUTOMATED_DESKTOP_APPROVAL.json"


@dataclass(frozen=True)
class AutomatedDesktopApprovalCheck:
    valid: bool
    status: str
    message: str
    generated_at: str = ""
    session_type: str = ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_automated_desktop_approval(project_root: Path) -> AutomatedDesktopApprovalCheck:
    report_path = project_root / REPORT_NAME
    if not report_path.is_file() or report_path.is_symlink():
        return AutomatedDesktopApprovalCheck(False, "missing", "Automatisierte Desktopprüfung fehlt.")
    try:
        data: dict[str, Any] = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return AutomatedDesktopApprovalCheck(False, "invalid", f"Desktopbericht ist unlesbar: {exc}")
    if data.get("schema_version") not in {1, 2} or data.get("status") != "passed":
        return AutomatedDesktopApprovalCheck(False, "invalid", "Desktopbericht meldet keinen bestandenen Zustand.")
    if str(data.get("build", "")) != build_label():
        return AutomatedDesktopApprovalCheck(False, "expired", "Desktopbericht gehört zu einem anderen Build.")
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks or any(not isinstance(item, dict) or item.get("passed") is not True for item in checks):
        return AutomatedDesktopApprovalCheck(False, "invalid", "Mindestens eine Desktopprüfung ist nicht bestanden.")
    screenshot_rel = str(data.get("screenshot", ""))
    if not screenshot_rel or Path(screenshot_rel).is_absolute() or ".." in Path(screenshot_rel).parts:
        return AutomatedDesktopApprovalCheck(False, "invalid", "Screenshotpfad ist ungültig.")
    screenshot = project_root / screenshot_rel
    if not screenshot.is_file() or screenshot.is_symlink():
        return AutomatedDesktopApprovalCheck(False, "invalid", "Desktop-Screenshot fehlt.")
    if sha256_file(screenshot) != str(data.get("screenshot_sha256", "")):
        return AutomatedDesktopApprovalCheck(False, "invalid", "Desktop-Screenshot wurde verändert.")
    generated_at = str(data.get("generated_at", ""))
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError:
        return AutomatedDesktopApprovalCheck(False, "invalid", "Zeitstempel ist ungültig.")
    session_type = str(data.get("session_type", "unknown"))
    return AutomatedDesktopApprovalCheck(True, "valid", "Automatisierte reale Desktopprüfung ist gültig.", generated_at, session_type)
