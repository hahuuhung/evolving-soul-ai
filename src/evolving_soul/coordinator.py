"""Optional, content-blind succession coordinator service."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from .crypto import (
    b64,
    canonical_json,
    decrypt,
    derive_key,
    encrypt,
    load_private_key,
    public_key_bytes,
    unb64,
)
from .errors import AuthenticationRequired, SoulError, SuccessionError
from .succession import PolicyRuntime, SuccessionState
from .types import SuccessionPolicy


@dataclass(slots=True)
class CoordinatorRecord:
    capsule_pseudonym: str
    owner_credential: dict[str, Any]
    guardian_credentials: dict[str, dict[str, Any]]
    runtime: PolicyRuntime
    notification_ciphertext: bytes
    coordinator_share_ciphertext: bytes


class CoordinatorRepository(Protocol):
    def put(self, record: CoordinatorRecord) -> None: ...

    def get(self, capsule_pseudonym: str) -> CoordinatorRecord: ...


class InMemoryCoordinatorRepository:
    """Deterministic test/demo repository; production uses PostgreSQL."""

    def __init__(self) -> None:
        self.records: dict[str, CoordinatorRecord] = {}

    def put(self, record: CoordinatorRecord) -> None:
        self.records[record.capsule_pseudonym] = record

    def get(self, capsule_pseudonym: str) -> CoordinatorRecord:
        try:
            return self.records[capsule_pseudonym]
        except KeyError as exc:
            raise SuccessionError("Unknown succession policy") from exc


class PostgresCoordinatorRepository:
    """Minimal PostgreSQL adapter; payloads contain no memory, CEK, or capsule data."""

    schema = """
    CREATE TABLE IF NOT EXISTS succession_policies (
      capsule_pseudonym TEXT PRIMARY KEY,
      owner_credential JSONB NOT NULL,
      guardian_credentials JSONB NOT NULL,
      policy JSONB NOT NULL,
      policy_hash TEXT NOT NULL,
      last_heartbeat TIMESTAMPTZ NOT NULL,
      state TEXT NOT NULL,
      guardian_assertions JSONB NOT NULL,
      released_at TIMESTAMPTZ,
      notification_ciphertext BYTEA NOT NULL,
      coordinator_share_ciphertext BYTEA NOT NULL
    )
    """

    def __init__(self, database_url: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise SoulError("PostgreSQL support requires evolving-soul-ai[coordinator]") from exc
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise SoulError("Coordinator production storage must be PostgreSQL")
        self._psycopg = psycopg
        self.database_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
        with self._connect() as connection:
            connection.execute(self.schema)

    def _connect(self) -> Any:
        return self._psycopg.connect(self.database_url)

    def put(self, record: CoordinatorRecord) -> None:
        runtime = record.runtime
        statement = """
        INSERT INTO succession_policies VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (capsule_pseudonym) DO UPDATE SET
          owner_credential=EXCLUDED.owner_credential,
          guardian_credentials=EXCLUDED.guardian_credentials,
          policy=EXCLUDED.policy,
          policy_hash=EXCLUDED.policy_hash,
          last_heartbeat=EXCLUDED.last_heartbeat,
          state=EXCLUDED.state,
          guardian_assertions=EXCLUDED.guardian_assertions,
          released_at=EXCLUDED.released_at,
          notification_ciphertext=EXCLUDED.notification_ciphertext,
          coordinator_share_ciphertext=EXCLUDED.coordinator_share_ciphertext
        """
        values = (
            record.capsule_pseudonym,
            json.dumps(record.owner_credential),
            json.dumps(record.guardian_credentials),
            json.dumps(asdict(runtime.policy)),
            runtime.policy_hash,
            runtime.last_heartbeat,
            runtime.state.value,
            json.dumps(
                {key: value.isoformat() for key, value in runtime.guardian_assertions.items()}
            ),
            runtime.released_at,
            record.notification_ciphertext,
            record.coordinator_share_ciphertext,
        )
        with self._connect() as connection:
            connection.execute(statement, values)

    def get(self, capsule_pseudonym: str) -> CoordinatorRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM succession_policies WHERE capsule_pseudonym=%s",
                (capsule_pseudonym,),
            ).fetchone()
        if row is None:
            raise SuccessionError("Unknown succession policy")
        policy_value = row[3] if isinstance(row[3], dict) else json.loads(row[3])
        assertions = row[7] if isinstance(row[7], dict) else json.loads(row[7])
        runtime = PolicyRuntime(
            policy=SuccessionPolicy(**policy_value),
            policy_hash=row[4],
            last_heartbeat=row[5],
            state=SuccessionState(row[6]),
            guardian_assertions={
                key: datetime.fromisoformat(value) for key, value in assertions.items()
            },
            released_at=row[8],
        )
        return CoordinatorRecord(
            capsule_pseudonym=row[0],
            owner_credential=row[1] if isinstance(row[1], dict) else json.loads(row[1]),
            guardian_credentials=row[2] if isinstance(row[2], dict) else json.loads(row[2]),
            runtime=runtime,
            notification_ciphertext=bytes(row[9]),
            coordinator_share_ciphertext=bytes(row[10]),
        )


class AssertionVerifier(Protocol):
    def verify(
        self, credential: dict[str, Any], response: dict[str, Any], challenge: bytes
    ) -> int: ...


class PyWebAuthnAssertionVerifier:
    def __init__(self, *, rp_id: str, origin: str) -> None:
        self.rp_id = rp_id
        self.origin = origin

    def verify(self, credential: dict[str, Any], response: dict[str, Any], challenge: bytes) -> int:
        try:
            from webauthn import verify_authentication_response
        except ImportError as exc:
            raise SoulError("WebAuthn requires evolving-soul-ai[coordinator]") from exc
        result = verify_authentication_response(
            credential=response,
            expected_challenge=challenge,
            expected_rp_id=self.rp_id,
            expected_origin=self.origin,
            credential_public_key=unb64(credential["public_key"]),
            credential_current_sign_count=int(credential["sign_count"]),
            require_user_verification=True,
        )
        return int(result.new_sign_count)


class ChallengeStore:
    def __init__(self) -> None:
        self.values: dict[str, tuple[str, str, bytes, datetime]] = {}

    def issue(self, pseudonym: str, actor: str) -> tuple[str, bytes]:
        challenge_id = secrets.token_urlsafe(18)
        challenge = secrets.token_bytes(32)
        self.values[challenge_id] = (
            pseudonym,
            actor,
            challenge,
            datetime.now(UTC) + timedelta(minutes=5),
        )
        return challenge_id, challenge

    def consume(self, challenge_id: str, pseudonym: str, actor: str) -> bytes:
        try:
            stored_pseudonym, stored_actor, challenge, expiry = self.values.pop(challenge_id)
        except KeyError as exc:
            raise AuthenticationRequired("Unknown or replayed coordinator challenge") from exc
        if (
            not hmac.compare_digest(stored_pseudonym, pseudonym)
            or not hmac.compare_digest(stored_actor, actor)
            or datetime.now(UTC) >= expiry
        ):
            raise AuthenticationRequired("Coordinator challenge is invalid or expired")
        return challenge


class CoordinatorService:
    def __init__(
        self,
        repository: CoordinatorRepository,
        *,
        deployment_key: bytes,
        verifier: AssertionVerifier,
    ) -> None:
        if len(deployment_key) < 32:
            raise ValueError("Coordinator deployment key must contain at least 256 bits")
        self.repository = repository
        self.deployment_key = derive_key(deployment_key, b"soul-coordinator/at-rest/v1")
        self.pseudonym_key = derive_key(deployment_key, b"soul-coordinator/pseudonym/v1")
        self.verifier = verifier
        self.challenges = ChallengeStore()
        # Stable across restarts without storing another secret; domain-separated
        # from database encryption and capsule pseudonyms.
        self.receipt_key = load_private_key(
            derive_key(deployment_key, b"soul-coordinator/receipt-signing/v1")
        )

    @property
    def receipt_public_key(self) -> str:
        return b64(public_key_bytes(self.receipt_key))

    def pseudonym(self, capsule_id: str) -> str:
        return hmac.new(self.pseudonym_key, capsule_id.encode(), hashlib.sha256).hexdigest()

    def _seal(self, value: str, purpose: str) -> bytes:
        nonce, ciphertext = encrypt(self.deployment_key, value.encode(), purpose.encode())
        return nonce + ciphertext

    def _open(self, value: bytes, purpose: str) -> str:
        return decrypt(self.deployment_key, value[:12], value[12:], purpose.encode()).decode()

    def provision(
        self,
        *,
        capsule_id: str,
        policy: SuccessionPolicy,
        policy_hash: str,
        owner_credential: dict[str, Any],
        guardian_credentials: dict[str, dict[str, Any]],
        notification_target: str,
        coordinator_share: str,
    ) -> str:
        pseudonym = self.pseudonym(capsule_id)
        runtime = PolicyRuntime.create(policy, datetime.now(UTC))
        runtime.policy_hash = policy_hash
        self.repository.put(
            CoordinatorRecord(
                capsule_pseudonym=pseudonym,
                owner_credential=owner_credential,
                guardian_credentials=guardian_credentials,
                runtime=runtime,
                notification_ciphertext=self._seal(notification_target, pseudonym + ":notify"),
                coordinator_share_ciphertext=self._seal(coordinator_share, pseudonym + ":share"),
            )
        )
        return pseudonym

    def challenge(self, capsule_id: str, actor: str) -> dict[str, str]:
        pseudonym = self.pseudonym(capsule_id)
        record = self.repository.get(pseudonym)
        if actor != "owner" and actor not in record.guardian_credentials:
            raise AuthenticationRequired("Actor is not registered for this policy")
        challenge_id, challenge = self.challenges.issue(pseudonym, actor)
        return {"challenge_id": challenge_id, "challenge": b64(challenge)}

    def assert_actor(
        self,
        *,
        capsule_id: str,
        actor: str,
        challenge_id: str,
        response: dict[str, Any],
    ) -> CoordinatorRecord:
        pseudonym = self.pseudonym(capsule_id)
        record = self.repository.get(pseudonym)
        challenge = self.challenges.consume(challenge_id, pseudonym, actor)
        credential = (
            record.owner_credential if actor == "owner" else record.guardian_credentials[actor]
        )
        credential["sign_count"] = self.verifier.verify(credential, response, challenge)
        return record

    def heartbeat(self, record: CoordinatorRecord) -> dict[str, Any]:
        now = datetime.now(UTC)
        record.runtime.heartbeat(now)
        self.repository.put(record)
        return self._signed_receipt(record, "heartbeat", now)

    def claim(self, record: CoordinatorRecord, guardian_id: str) -> dict[str, Any]:
        now = datetime.now(UTC)
        record.runtime.guardian_claim(guardian_id, now)
        self.repository.put(record)
        return self._signed_receipt(record, "guardian-claim", now)

    def release(self, capsule_id: str) -> dict[str, Any]:
        pseudonym = self.pseudonym(capsule_id)
        record = self.repository.get(pseudonym)
        now = datetime.now(UTC)
        record.runtime.release(now)
        self.repository.put(record)
        return {
            "coordinator_share": self._open(
                record.coordinator_share_ciphertext, pseudonym + ":share"
            ),
            "receipt": self._signed_receipt(record, "release", now),
        }

    def _signed_receipt(
        self, record: CoordinatorRecord, event: str, occurred_at: datetime
    ) -> dict[str, Any]:
        payload = {
            "capsule_pseudonym": record.capsule_pseudonym,
            "event": event,
            "occurred_at": occurred_at.isoformat(),
            "state": record.runtime.state.value,
            "policy_hash": record.runtime.policy_hash,
        }
        return {
            "payload": payload,
            "signature": b64(self.receipt_key.sign(canonical_json(payload))),
        }


def create_coordinator_app(service: CoordinatorService, *, provisioning_token: str) -> Any:
    try:
        from fastapi import FastAPI, Header, HTTPException
    except ImportError as exc:
        raise SoulError("Coordinator API requires evolving-soul-ai[coordinator]") from exc
    app = FastAPI(title="Evolving Soul Coordinator", version="3.0.0a1")

    def authorize(value: str | None) -> None:
        if (
            not value
            or not value.startswith("Bearer ")
            or not hmac.compare_digest(value[7:], provisioning_token)
        ):
            raise HTTPException(401, "Invalid provisioning credential")

    @app.get("/v1/health")
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/v1/metadata")
    def metadata() -> dict[str, str]:
        return {
            "receipt_public_key": service.receipt_public_key,
            "receipt_algorithm": "Ed25519",
            "time_authority": "coordinator-utc",
        }

    @app.post("/v1/policies")
    def provision(
        body: dict[str, Any], authorization: str | None = Header(default=None)
    ) -> dict[str, str]:
        authorize(authorization)
        policy = SuccessionPolicy(**body["policy"])
        pseudonym = service.provision(
            capsule_id=body["capsule_id"],
            policy=policy,
            policy_hash=body["policy_hash"],
            owner_credential=body["owner_credential"],
            guardian_credentials=body["guardian_credentials"],
            notification_target=body["notification_target"],
            coordinator_share=body["coordinator_share"],
        )
        return {"capsule_pseudonym": pseudonym, "state": "ACTIVE"}

    @app.post("/v1/challenges")
    def challenge(body: dict[str, Any]) -> dict[str, str]:
        return service.challenge(body["capsule_id"], body["actor"])

    @app.post("/v1/heartbeat")
    def heartbeat(body: dict[str, Any]) -> dict[str, Any]:
        record = service.assert_actor(
            capsule_id=body["capsule_id"],
            actor="owner",
            challenge_id=body["challenge_id"],
            response=body["assertion"],
        )
        return service.heartbeat(record)

    @app.post("/v1/guardian/claim")
    def guardian_claim(body: dict[str, Any]) -> dict[str, Any]:
        guardian_id = body["guardian_id"]
        record = service.assert_actor(
            capsule_id=body["capsule_id"],
            actor=guardian_id,
            challenge_id=body["challenge_id"],
            response=body["assertion"],
        )
        return service.claim(record, guardian_id)

    @app.post("/v1/release")
    def release(body: dict[str, Any]) -> dict[str, Any]:
        guardian_id = body["guardian_id"]
        # Never return a coordinator share to a caller that did not just prove
        # control of one of the policy's guardian passkeys.
        service.assert_actor(
            capsule_id=body["capsule_id"],
            actor=guardian_id,
            challenge_id=body["challenge_id"],
            response=body["assertion"],
        )
        return service.release(body["capsule_id"])

    return app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soul-coordinator")
    parser.add_argument("--database-url-file", required=True)
    parser.add_argument("--deployment-key-file", required=True)
    parser.add_argument("--provisioning-token-file", required=True)
    parser.add_argument("--rp-id", required=True)
    parser.add_argument("--origin", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args(argv)
    database_url = Path(args.database_url_file).read_text(encoding="utf-8").strip()
    deployment_key = unb64(Path(args.deployment_key_file).read_text(encoding="utf-8").strip())
    provisioning_token = Path(args.provisioning_token_file).read_text(encoding="utf-8").strip()
    repository = PostgresCoordinatorRepository(database_url)
    service = CoordinatorService(
        repository,
        deployment_key=deployment_key,
        verifier=PyWebAuthnAssertionVerifier(rp_id=args.rp_id, origin=args.origin),
    )
    app = create_coordinator_app(service, provisioning_token=provisioning_token)
    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
