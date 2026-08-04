from __future__ import annotations

import ctypes
import ctypes.util
import errno
from dataclasses import dataclass


class SeccompUnavailable(RuntimeError):
    pass


BLOCKED_SYSCALLS = (
    "execve",
    "execveat",
    "fork",
    "vfork",
    "clone",
    "clone3",
    "socket",
    "socketpair",
    "connect",
    "bind",
    "listen",
    "accept",
    "accept4",
    "mount",
    "umount2",
    "ptrace",
    "bpf",
    "keyctl",
    "unshare",
    "setns",
    "open_by_handle_at",
    "name_to_handle_at",
)


@dataclass(frozen=True, slots=True)
class SeccompPolicy:
    blocked_syscalls: tuple[str, ...] = BLOCKED_SYSCALLS
    errno_value: int = errno.EPERM


class SeccompInstaller:
    def __init__(self, library: ctypes.CDLL, policy: SeccompPolicy | None = None) -> None:
        self.library = library
        self.policy = policy or SeccompPolicy()
        self._configure_library()

    def _configure_library(self) -> None:
        lib = self.library
        lib.seccomp_init.argtypes = [ctypes.c_uint32]
        lib.seccomp_init.restype = ctypes.c_void_p
        lib.seccomp_release.argtypes = [ctypes.c_void_p]
        lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
        lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
        lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
        lib.seccomp_rule_add.restype = ctypes.c_int
        lib.seccomp_load.argtypes = [ctypes.c_void_p]
        lib.seccomp_load.restype = ctypes.c_int

    def install(self) -> None:
        context = self.library.seccomp_init(0x7FFF0000)
        if not context:
            raise SeccompUnavailable("Seccomp-Kontext konnte nicht erstellt werden.")
        try:
            self._add_rules(context)
            if self.library.seccomp_load(context) != 0:
                raise SeccompUnavailable("Seccomp-Filter konnte nicht aktiviert werden.")
        finally:
            self.library.seccomp_release(context)

    def _add_rules(self, context: ctypes.c_void_p) -> None:
        action = 0x00050000 | self.policy.errno_value
        for name in self.policy.blocked_syscalls:
            number = self.library.seccomp_syscall_resolve_name(name.encode("ascii"))
            if number < 0:
                continue
            if self.library.seccomp_rule_add(context, action, number, 0) != 0:
                raise SeccompUnavailable(f"Seccomp-Regel für {name} konnte nicht gesetzt werden.")


def find_seccomp_library() -> str:
    discovered = ctypes.util.find_library("seccomp")
    candidates = (
        discovered,
        "/lib/x86_64-linux-gnu/libseccomp.so.2",
        "/lib/aarch64-linux-gnu/libseccomp.so.2",
        "/usr/lib/x86_64-linux-gnu/libseccomp.so.2",
    )
    for candidate in candidates:
        if candidate and _library_works(candidate):
            return candidate
    raise SeccompUnavailable("libseccomp wurde nicht gefunden.")


def _library_works(candidate: str) -> bool:
    try:
        ctypes.CDLL(candidate)
        return True
    except OSError:
        return False


def install_seccomp_policy() -> None:
    library = ctypes.CDLL(find_seccomp_library(), use_errno=True)
    SeccompInstaller(library).install()
