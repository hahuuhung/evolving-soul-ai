"""Local FastAPI control plane. The vault remains usable without a coordinator."""

from __future__ import annotations

import secrets
import hashlib
import hmac
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from .auth import BootstrapManager, PairingTokenManager
from .errors import AuthenticationRequired, SoulError
from .types import Provenance
from .vault import SoulVault
from .webauthn_auth import WebAuthnManager


class StepUpSessions:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, datetime]] = {}

    def issue(self, credential_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (credential_id, datetime.now(UTC) + timedelta(minutes=5))
        return token

    def consume(self, token: str) -> str:
        try:
            credential_id, expiry = self._sessions.pop(token)
        except KeyError as exc:
            raise AuthenticationRequired("A fresh passkey step-up is required") from exc
        if datetime.now(UTC) >= expiry:
            raise AuthenticationRequired("Passkey step-up session expired")
        return credential_id


def create_app(
    vault: SoulVault,
    *,
    rp_id: str = "localhost",
    origin: str = "http://localhost:8765",
) -> Any:
    try:
        from fastapi import FastAPI, Header, HTTPException
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise SoulError("Local server requires evolving-soul-ai[server]") from exc
    if vault._store is None:  # The server must never silently unlock a vault.
        raise SoulError("Vault must be unlocked before starting the sidecar")

    app = FastAPI(title="Evolving Soul local sidecar", version="3.0.0a1")
    bootstrap = BootstrapManager()
    bootstrap_code = bootstrap.issue()
    passkeys = WebAuthnManager(vault._store, rp_id=rp_id, origin=origin)
    pairing = PairingTokenManager()
    sessions = StepUpSessions()
    review_secret = secrets.token_bytes(32)
    app.state.bootstrap_code = bootstrap_code

    def problem(exc: Exception, status: int = 401) -> HTTPException:
        return HTTPException(status_code=status, detail=str(exc))

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "vault": "unlocked", "capsule_id": vault.capsule_id}

    @app.get("/", response_class=HTMLResponse)
    def local_review() -> str:
        return (
            "<main><h1>Evolving Soul AI</h1><p>Local review service is running.</p>"
            "<p>Use a passkey-authenticated client to approve or reject proposals.</p></main>"
        )

    @app.post("/v1/bootstrap/register/options")
    def bootstrap_options(body: dict[str, Any]) -> dict[str, Any]:
        try:
            bootstrap.consume(str(body.get("code", "")))
            return passkeys.registration_options(str(body.get("owner_name", "Owner")))
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/bootstrap/register/complete")
    def bootstrap_complete(body: dict[str, Any]) -> dict[str, str]:
        try:
            credential_id = passkeys.complete_registration(
                str(body["ceremony_id"]), body["credential"]
            )
            return {"credential_id": credential_id}
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/auth/options")
    def auth_options() -> dict[str, Any]:
        try:
            return passkeys.authentication_options()
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/auth/complete")
    def auth_complete(body: dict[str, Any]) -> dict[str, str]:
        try:
            credential_id = passkeys.complete_authentication(
                str(body["ceremony_id"]), body["credential"]
            )
            return {"step_up_token": sessions.issue(credential_id), "expires_in": "300"}
        except Exception as exc:
            raise problem(exc) from exc

    def consume_step_up(authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationRequired("Bearer step-up token required")
        return sessions.consume(authorization[7:])

    @app.post("/v1/pair/open-webui")
    def pair_open_webui(
        body: dict[str, Any], authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        try:
            consume_step_up(authorization)
            user_id = str(body["user_id"])
            return {
                "token": pairing.issue(user_id),
                "scopes": sorted(PairingTokenManager.allowed_scopes),
            }
        except Exception as exc:
            raise problem(exc) from exc

    def plugin_auth(authorization: str | None, user_id: str | None, scope: str) -> None:
        if not authorization or not authorization.startswith("Bearer ") or not user_id:
            raise AuthenticationRequired("Bound pairing token required")
        pairing.verify(authorization[7:], user_id, scope)

    @app.post("/v1/context/search")
    def context_search(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "context:read")
            records = vault.search_context(
                str(body.get("query", "")), token_budget=min(int(body.get("token_budget", 1024)), 4096)
            )
            return {
                "context": [
                    {
                        "memory_id": record.memory_id,
                        "content": record.content,
                        "provenance": asdict(record.provenance),
                        "trust": "untrusted-memory-data",
                    }
                    for record in records
                ]
            }
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals")
    def create_proposal(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "proposal:create")
            proposal = vault.propose_memory(
                str(body["content"])[:4_000],
                provenance=Provenance(
                    source=f"open-webui:{x_open_webui_user_id}",
                    extractor=str(body.get("extractor", "open-webui-filter")),
                ),
            )
            return asdict(proposal)
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/review-link")
    def review_link(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "context:read")
            expires = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
            proposal_id = str(body.get("proposal_id", "queue"))
            signed = f"{proposal_id}:{expires}"
            signature = hmac.new(review_secret, signed.encode(), hashlib.sha256).hexdigest()
            return {
                "url": f"{origin}/?review={proposal_id}&expires={expires}&sig={signature}",
                "expires_at": datetime.fromtimestamp(expires, UTC).isoformat(),
            }
        except Exception as exc:
            raise problem(exc) from exc

    @app.get("/v1/proposals")
    def list_proposals(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        try:
            consume_step_up(authorization)
            return [asdict(item) for item in vault.list_proposals()]
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals/{proposal_id}/approve")
    def approve(
        proposal_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            credential_id = consume_step_up(authorization)
            return asdict(
                vault.approve_memory(
                    proposal_id,
                    actor_credential_id=credential_id,
                    edited_content=body.get("content"),
                    owner_asserted=True,
                )
            )
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals/{proposal_id}/reject", status_code=204)
    def reject(proposal_id: str, authorization: str | None = Header(default=None)) -> None:
        try:
            consume_step_up(authorization)
            vault.reject_memory(proposal_id, owner_asserted=True)
        except Exception as exc:
            raise problem(exc) from exc

    return app
