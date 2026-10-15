"""WebAuthn ceremony adapter using py_webauthn with replay-safe challenges."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from .crypto import b64, unb64
from .errors import AuthenticationRequired, SoulError
from .storage import EncryptedStore


class WebAuthnManager:
    def __init__(self, store: EncryptedStore, *, rp_id: str, origin: str) -> None:
        self.store = store
        self.rp_id = rp_id
        self.origin = origin
        self._challenges: dict[str, tuple[str, bytes, datetime]] = {}

    @staticmethod
    def _library():
        try:
            import webauthn
        except ImportError as exc:
            raise SoulError(
                "Passkey support requires evolving-soul-ai[server]"
            ) from exc
        return webauthn

    def _save_challenge(self, purpose: str, challenge: bytes) -> str:
        ceremony_id = secrets.token_urlsafe(18)
        self._challenges[ceremony_id] = (
            purpose,
            challenge,
            datetime.now(UTC) + timedelta(minutes=5),
        )
        return ceremony_id

    def _consume_challenge(self, ceremony_id: str, purpose: str) -> bytes:
        try:
            stored_purpose, challenge, expires_at = self._challenges.pop(ceremony_id)
        except KeyError as exc:
            raise AuthenticationRequired("Unknown or replayed WebAuthn ceremony") from exc
        if stored_purpose != purpose or datetime.now(UTC) >= expires_at:
            raise AuthenticationRequired("WebAuthn ceremony is expired or has the wrong purpose")
        return challenge

    def credentials(self) -> list[dict[str, Any]]:
        return [value for _, value in self.store.iter_objects("passkey")]

    def registration_options(self, owner_name: str) -> dict[str, Any]:
        webauthn = self._library()
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            ResidentKeyRequirement,
            UserVerificationRequirement,
        )

        challenge = secrets.token_bytes(32)
        options = webauthn.generate_registration_options(
            rp_id=self.rp_id,
            rp_name="Evolving Soul AI",
            user_id=secrets.token_bytes(32),
            user_name=owner_name,
            challenge=challenge,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
        )
        return {
            "ceremony_id": self._save_challenge("register", challenge),
            "options": json.loads(webauthn.options_to_json(options)),
        }

    def complete_registration(self, ceremony_id: str, credential: dict[str, Any]) -> str:
        webauthn = self._library()
        challenge = self._consume_challenge(ceremony_id, "register")
        verification = webauthn.verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=self.origin,
            expected_rp_id=self.rp_id,
            require_user_verification=True,
        )
        credential_id = b64(verification.credential_id)
        value = {
            "credential_id": credential_id,
            "public_key": b64(verification.credential_public_key),
            "sign_count": verification.sign_count,
            "device_type": str(verification.credential_device_type),
            "backed_up": verification.credential_backed_up,
            "created_at": datetime.now(UTC).isoformat(),
            "revoked": False,
        }
        self.store.put(secrets.token_bytes(24), "passkey", value)
        return credential_id

    def authentication_options(self) -> dict[str, Any]:
        webauthn = self._library()
        from webauthn.helpers.structs import (
            PublicKeyCredentialDescriptor,
            UserVerificationRequirement,
        )

        active = [item for item in self.credentials() if not item["revoked"]]
        if not active:
            raise AuthenticationRequired("No owner passkey is registered")
        challenge = secrets.token_bytes(32)
        options = webauthn.generate_authentication_options(
            rp_id=self.rp_id,
            challenge=challenge,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=unb64(item["credential_id"])) for item in active
            ],
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        return {
            "ceremony_id": self._save_challenge("authenticate", challenge),
            "options": json.loads(webauthn.options_to_json(options)),
        }

    def complete_authentication(self, ceremony_id: str, credential: dict[str, Any]) -> str:
        webauthn = self._library()
        challenge = self._consume_challenge(ceremony_id, "authenticate")
        supplied_id = credential.get("id", "")
        stored = next(
            (
                (opaque_id, item)
                for opaque_id, item in self.store.iter_objects("passkey")
                if not item["revoked"] and secrets.compare_digest(item["credential_id"], supplied_id)
            ),
            None,
        )
        if stored is None:
            raise AuthenticationRequired("Unknown or revoked passkey")
        opaque_id, item = stored
        verification = webauthn.verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.origin,
            credential_public_key=unb64(item["public_key"]),
            credential_current_sign_count=int(item["sign_count"]),
            require_user_verification=True,
        )
        item["sign_count"] = verification.new_sign_count
        item["last_used_at"] = datetime.now(UTC).isoformat()
        self.store.put(opaque_id, "passkey", item)
        return item["credential_id"]

    def revoke_credential(self, credential_id: str) -> None:
        active = 0
        target = None
        for opaque_id, item in self.store.iter_objects("passkey"):
            if not item["revoked"]:
                active += 1
            if secrets.compare_digest(item["credential_id"], credential_id):
                target = (opaque_id, item)
        if target is None:
            raise AuthenticationRequired("Unknown passkey")
        if active <= 1 and not target[1]["revoked"]:
            raise AuthenticationRequired("Cannot revoke the final owner passkey")
        target[1]["revoked"] = True
        self.store.put(target[0], "passkey", target[1])

