from __future__ import annotations

import ctypes
import os
import platform
import resource
import shutil
import subprocess
from dataclasses import dataclass

try:
    from .sandbox_seccomp import SeccompUnavailable, find_seccomp_library, install_seccomp_policy
except ImportError:  # standalone import inside the chrooted plugin host
    from sandbox_seccomp import SeccompUnavailable, find_seccomp_library, install_seccomp_policy

PR_SET_NO_NEW_PRIVS = 38
LANDLOCK_CREATE_RULESET_VERSION = 1

# Linux UAPI access bits. The ABI query decides which newer bits are enabled.
LANDLOCK_ACCESS_FS_EXECUTE = 1 << 0
LANDLOCK_ACCESS_FS_WRITE_FILE = 1 << 1
LANDLOCK_ACCESS_FS_READ_FILE = 1 << 2
LANDLOCK_ACCESS_FS_READ_DIR = 1 << 3
LANDLOCK_ACCESS_FS_REMOVE_DIR = 1 << 4
LANDLOCK_ACCESS_FS_REMOVE_FILE = 1 << 5
LANDLOCK_ACCESS_FS_MAKE_CHAR = 1 << 6
LANDLOCK_ACCESS_FS_MAKE_DIR = 1 << 7
LANDLOCK_ACCESS_FS_MAKE_REG = 1 << 8
LANDLOCK_ACCESS_FS_MAKE_SOCK = 1 << 9
LANDLOCK_ACCESS_FS_MAKE_FIFO = 1 << 10
LANDLOCK_ACCESS_FS_MAKE_BLOCK = 1 << 11
LANDLOCK_ACCESS_FS_MAKE_SYM = 1 << 12
LANDLOCK_ACCESS_FS_REFER = 1 << 13
LANDLOCK_ACCESS_FS_TRUNCATE = 1 << 14
LANDLOCK_ACCESS_FS_IOCTL_DEV = 1 << 15


class SandboxUnavailable(RuntimeError):
    pass


class _LandlockRulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


@dataclass(frozen=True, slots=True)
class SandboxStatus:
    available: bool
    message: str
    landlock_abi: int = 0
    seccomp: bool = False


def _syscall_numbers() -> tuple[int, int]:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64", "aarch64", "arm64", "riscv64"}:
        return 444, 446
    raise SandboxUnavailable(f"Landlock-Syscallnummern für {machine} sind nicht registriert.")


def _landlock_abi(libc: ctypes.CDLL) -> int:
    create_ruleset, _ = _syscall_numbers()
    result = libc.syscall(create_ruleset, 0, 0, LANDLOCK_CREATE_RULESET_VERSION)
    if result < 0:
        error = ctypes.get_errno()
        raise SandboxUnavailable(f"Landlock ist nicht verfügbar: {os.strerror(error)}")
    return int(result)


def _handled_rights(abi: int) -> int:
    rights = (
        LANDLOCK_ACCESS_FS_EXECUTE
        | LANDLOCK_ACCESS_FS_WRITE_FILE
        | LANDLOCK_ACCESS_FS_READ_FILE
        | LANDLOCK_ACCESS_FS_READ_DIR
        | LANDLOCK_ACCESS_FS_REMOVE_DIR
        | LANDLOCK_ACCESS_FS_REMOVE_FILE
        | LANDLOCK_ACCESS_FS_MAKE_CHAR
        | LANDLOCK_ACCESS_FS_MAKE_DIR
        | LANDLOCK_ACCESS_FS_MAKE_REG
        | LANDLOCK_ACCESS_FS_MAKE_SOCK
        | LANDLOCK_ACCESS_FS_MAKE_FIFO
        | LANDLOCK_ACCESS_FS_MAKE_BLOCK
        | LANDLOCK_ACCESS_FS_MAKE_SYM
    )
    if abi >= 2:
        rights |= LANDLOCK_ACCESS_FS_REFER
    if abi >= 3:
        rights |= LANDLOCK_ACCESS_FS_TRUNCATE
    if abi >= 5:
        rights |= LANDLOCK_ACCESS_FS_IOCTL_DEV
    return rights


def _apply_landlock_deny_all() -> int:
    if platform.system() != "Linux":
        raise SandboxUnavailable("Landlock ist nur unter Linux verfügbar.")
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    abi = _landlock_abi(libc)
    create_ruleset, restrict_self = _syscall_numbers()
    attr = _LandlockRulesetAttr(_handled_rights(abi))
    fd = libc.syscall(create_ruleset, ctypes.byref(attr), ctypes.sizeof(attr), 0)
    if fd < 0:
        error = ctypes.get_errno()
        raise SandboxUnavailable(f"Landlock-Regelsatz konnte nicht erstellt werden: {os.strerror(error)}")
    try:
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            error = ctypes.get_errno()
            raise SandboxUnavailable(f"no_new_privs konnte nicht gesetzt werden: {os.strerror(error)}")
        if libc.syscall(restrict_self, fd, 0) != 0:
            error = ctypes.get_errno()
            raise SandboxUnavailable(f"Landlock konnte nicht aktiviert werden: {os.strerror(error)}")
    finally:
        os.close(fd)
    return abi


def _seccomp_library() -> str:
    try:
        return find_seccomp_library()
    except SeccompUnavailable as exc:
        raise SandboxUnavailable(str(exc)) from exc


def _apply_seccomp_deny_dangerous() -> None:
    try:
        install_seccomp_policy()
    except SeccompUnavailable as exc:
        raise SandboxUnavailable(str(exc)) from exc


def _apply_resource_limits() -> None:
    limits = {
        resource.RLIMIT_CPU: (3, 4),
        resource.RLIMIT_AS: (256 * 1024 * 1024, 256 * 1024 * 1024),
        resource.RLIMIT_FSIZE: (1024 * 1024, 1024 * 1024),
        resource.RLIMIT_NOFILE: (16, 16),
        resource.RLIMIT_CORE: (0, 0),
    }
    for key, value in limits.items():
        try:
            resource.setrlimit(key, value)
        except (OSError, ValueError):
            pass


def apply_plugin_sandbox() -> SandboxStatus:
    _apply_resource_limits()
    abi = 0
    landlock_message = ""
    try:
        abi = _apply_landlock_deny_all()
        landlock_message = f"Landlock ABI {abi}, "
    except SandboxUnavailable as exc:
        if os.environ.get("VIDEOBATCH_CHROOT_SANDBOX") != "1":
            raise
        landlock_message = f"Chroot-Dateisystemgrenze aktiv; Landlock optional nicht verfügbar ({exc}), "
    _apply_seccomp_deny_dangerous()
    return SandboxStatus(True, landlock_message + "Seccomp und Ressourcenlimits aktiv.", abi, True)


def _probe_namespace_support() -> tuple[bool, str]:
    binary = shutil.which("unshare")
    if not binary:
        return False, "unshare fehlt; Plugin-Ausführung bleibt sicher deaktiviert."
    command = [
        binary,
        "--user",
        "--map-root-user",
        "--net",
        "--pid",
        "--mount",
        "--fork",
        "true",
    ]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
            check=False,
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Linux-Namespace-Prüfung fehlgeschlagen: {exc}"
    if completed.returncode:
        detail = (completed.stderr or "").strip().splitlines()
        suffix = detail[-1] if detail else f"Code {completed.returncode}"
        return False, f"Linux-Namespaces sind auf diesem System blockiert: {suffix}"
    return True, ""


def probe_sandbox_support() -> SandboxStatus:
    if platform.system() != "Linux":
        return SandboxStatus(False, "Echte Plugin-Isolierung wird nur unter Linux unterstützt.")
    namespaces_ok, namespace_message = _probe_namespace_support()
    if not namespaces_ok:
        return SandboxStatus(False, namespace_message)
    try:
        _seccomp_library()
    except SandboxUnavailable as exc:
        return SandboxStatus(False, str(exc))
    abi = 0
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        abi = _landlock_abi(libc)
    except SandboxUnavailable:
        pass
    return SandboxStatus(True, "Chroot/Namespace/Seccomp-Isolierung ist verfügbar.", abi, True)
