"""OS keyring boundary for the local master key."""

from __future__ import annotations

from typing import Any, Protocol

from .crypto import b64, unb64
from .errors import SoulError


class KeyStore(Protocol):
    def set(self, capsule_id: str, key: bytes) -> None: ...

    def get(self, capsule_id: str) -> bytes: ...

    def delete(self, capsule_id: str) -> None: ...


class PlatformKeyring:
    service_name = "evolving-soul-ai"

    @staticmethod
    def _module() -> Any:
        try:
            import keyring
        except ImportError as exc:
            raise SoulError(
                "OS keyring support is required; install evolving-soul-ai[server]"
            ) from exc
        return keyring

    def set(self, capsule_id: str, key: bytes) -> None:
        self._module().set_password(self.service_name, capsule_id, b64(key))

    def get(self, capsule_id: str) -> bytes:
        value = self._module().get_password(self.service_name, capsule_id)
        if value is None:
            raise SoulError("Master key is not present in the OS keyring")
        return unb64(value)

    def delete(self, capsule_id: str) -> None:
        module = self._module()
        try:
            module.delete_password(self.service_name, capsule_id)
        except module.errors.PasswordDeleteError:
            pass


class MemoryKeyStore:
    """Explicit test adapter; never selected by production code."""

    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def set(self, capsule_id: str, key: bytes) -> None:
        self.values[capsule_id] = key

    def get(self, capsule_id: str) -> bytes:
        return self.values[capsule_id]

    def delete(self, capsule_id: str) -> None:
        self.values.pop(capsule_id, None)
