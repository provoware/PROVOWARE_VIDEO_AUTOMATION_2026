from __future__ import annotations

import json
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from os_sandbox import SandboxUnavailable, apply_plugin_sandbox

_SAFE_BUILTINS = MappingProxyType(
    {
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "range": range,
        "set": set,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "ValueError": ValueError,
        "TypeError": TypeError,
    }
)


def _execute_validator(source: str, payload: dict[str, Any]) -> bool:
    code = compile(source, "<signed-validator-plugin>", "exec", dont_inherit=True, optimize=2)
    apply_plugin_sandbox()
    namespace: dict[str, Any] = {"__builtins__": _SAFE_BUILTINS, "__name__": "videobatch_validator_plugin"}
    exec(code, namespace, namespace)  # nosec B102 - signed code runs after namespace/chroot/seccomp isolation
    validator = namespace.get("validate")
    if not callable(validator):
        raise RuntimeError("Validator-Plugin erwartet validate(payload).")
    return bool(validator(payload))


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if len(args) != 3:
        print(json.dumps({"ok": False, "error": "Aufruf erwartet: <plugin_dir> <capability> <payload_json>"}))
        return 2
    plugin_dir = Path(args[0]).expanduser().resolve()
    capability = args[1]
    try:
        payload = json.loads(args[2])
        if not isinstance(payload, dict):
            raise ValueError("Plugin-Nutzdaten müssen ein JSON-Objekt sein.")
        if capability != "validator":
            raise RuntimeError(f"Nicht implementierte Plugin-Fähigkeit ist gesperrt: {capability}")
        source = (plugin_dir / "plugin.py").read_text(encoding="utf-8")
        result = _execute_validator(source, payload)
        print(json.dumps({"ok": True, "result": result, "sandbox": "landlock+seccomp+user+network namespace"}))
        return 0
    except SandboxUnavailable as exc:
        print(json.dumps({"ok": False, "error": f"OS-Isolierung nicht verfügbar: {exc}"}))
        return 3
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
