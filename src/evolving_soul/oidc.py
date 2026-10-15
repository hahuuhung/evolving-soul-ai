"""Optional OIDC account linking. OIDC is never an unlock or step-up factor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import AuthenticationRequired, SoulError


@dataclass(frozen=True, slots=True)
class LinkedIdentity:
    issuer: str
    subject: str
    display_name: str | None = None


class OIDCAccountLinker:
    def __init__(self, issuer: str, client_id: str, client_secret: str) -> None:
        try:
            from authlib.integrations.httpx_client import AsyncOAuth2Client
        except ImportError as exc:
            raise SoulError("OIDC linking requires evolving-soul-ai[server]") from exc
        self.issuer = issuer.rstrip("/")
        self.client = AsyncOAuth2Client(client_id, client_secret)

    async def identity_from_userinfo(self, token: dict[str, Any]) -> LinkedIdentity:
        response = await self.client.get(self.issuer + "/userinfo", token=token)
        response.raise_for_status()
        claims = response.json()
        if not claims.get("sub"):
            raise AuthenticationRequired("OIDC userinfo response has no subject")
        return LinkedIdentity(
            issuer=self.issuer,
            subject=str(claims["sub"]),
            display_name=claims.get("name"),
        )

    @staticmethod
    def authorize_sensitive_operation(_identity: LinkedIdentity) -> None:
        raise AuthenticationRequired(
            "OIDC can link an account but cannot unlock a capsule or authorize succession"
        )
