"""Bootstrap and scoped sidecar token primitives."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .crypto import b64, canonical_json, unb64
from .errors import AuthenticationRequired


@dataclass(slots=True)
class BootstrapCode:
    code: str
    expires_at: datetime


class BootstrapManager:
    def __init__(self) -> None:
        self._digest: bytes | None = None
        self._expires_at: datetime | None = None
        self._used = False

    def issue(self) -> BootstrapCode:
        code = "-".join(f"{secrets.randbelow(10_000):04d}" for _ in range(3))
        self._digest = hashlib.sha256(code.encode()).digest()
        self._expires_at = datetime.now(UTC) + timedelta(minutes=10)
        self._used = False
        return BootstrapCode(code=code, expires_at=self._expires_at)

    def consume(self, code: str) -> None:
        if self._digest is None or self._expires_at is None or self._used:
            raise AuthenticationRequired("Bootstrap code is unavailable or already used")
        valid = hmac.compare_digest(hashlib.sha256(code.encode()).digest(), self._digest)
        if not valid or datetime.now(UTC) >= self._expires_at:
            raise AuthenticationRequired("Bootstrap code is invalid or expired")
        self._used = True
        self._digest = None


class PairingTokenManager:
    allowed_scopes = frozenset({"context:read", "proposal:create"})

    def __init__(self, signing_secret: bytes | None = None) -> None:
        self._secret = signing_secret or os.urandom(32)
        self._revoked: set[str] = set()

    def issue(self, open_webui_user_id: str, expires_in: timedelta = timedelta(days=30)) -> str:
        if not open_webui_user_id:
            raise ValueError("Pairing tokens must be bound to an Open WebUI user ID")
        payload = {
            "jti": secrets.token_urlsafe(12),
            "sub": open_webui_user_id,
            "scopes": sorted(self.allowed_scopes),
            "exp": int((datetime.now(UTC) + expires_in).timestamp()),
        }
        encoded = b64(canonical_json(payload))
        signature = b64(hmac.digest(self._secret, encoded.encode(), "sha256"))
        return f"soul_v1.{encoded}.{signature}"

    def verify(self, token: str, user_id: str, required_scope: str) -> dict:
        try:
            prefix, encoded, signature = token.split(".")
            expected = hmac.digest(self._secret, encoded.encode(), "sha256")
            if prefix != "soul_v1" or not hmac.compare_digest(unb64(signature), expected):
                raise ValueError
            payload = json.loads(unb64(encoded))
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            raise AuthenticationRequired("Invalid pairing token") from exc
        if (
            payload["jti"] in self._revoked
            or payload["sub"] != user_id
            or required_scope not in payload["scopes"]
            or datetime.now(UTC).timestamp() >= payload["exp"]
        ):
            raise AuthenticationRequired("Pairing token is expired, revoked, or out of scope")
        return payload

    def revoke(self, token: str) -> None:
        try:
            payload = json.loads(unb64(token.split(".")[1]))
            self._revoked.add(payload["jti"])
        except (IndexError, KeyError, json.JSONDecodeError, ValueError):
            return


def require_step_up(owner_asserted: bool) -> None:
    if not owner_asserted:
        raise AuthenticationRequired("A fresh passkey assertion is required")
