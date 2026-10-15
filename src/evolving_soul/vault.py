"""High-level owner-bound local vault API."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .auth import require_step_up
from .capsule import SoulCapsule
from .crypto import (
    b64,
    canonical_json,
    decrypt,
    derive_key,
    encrypt,
    load_private_key,
    new_signing_key,
    private_key_bytes,
    public_key_bytes,
    random_key,
    unb64,
)
from .errors import SoulError, VaultLockedError
from .keyring_store import KeyStore, PlatformKeyring
from .memory import MemoryRepository, search_bm25
from .storage import EncryptedStore
from .succession import ReleaseShares, create_release_shares
from .types import (
    CapsuleHeader,
    Compartment,
    MemoryProposal,
    MemoryRecord,
    Provenance,
    SuccessionPolicy,
)

STATE_FILE = "vault.json"
DATABASE_FILE = "objects.sqlite3"


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(canonical_json(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


class SoulVault:
    def __init__(self, path: Path, metadata: dict[str, Any], key_store: KeyStore) -> None:
        self.path = path
        self.metadata = metadata
        self.key_store = key_store
        self._root_key: bytes | None = None
        self._signing_key = None
        self._store: EncryptedStore | None = None
        self._memory: MemoryRepository | None = None

    @property
    def capsule_id(self) -> str:
        return str(self.metadata["capsule_id"])

    @classmethod
    def create(cls, path: str | Path, *, key_store: KeyStore | None = None) -> SoulVault:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        state_path = path / STATE_FILE
        if state_path.exists():
            raise SoulError("A vault already exists at this path")
        key_store = key_store or PlatformKeyring()
        capsule_id = str(uuid.uuid4())
        root_key = random_key()
        signing_key = new_signing_key()
        nonce, encrypted_signing_key = encrypt(
            derive_key(root_key, b"soul-vault/signing-key/v1"),
            private_key_bytes(signing_key),
            capsule_id.encode(),
        )
        metadata = {
            "format": "evolving-soul-vault",
            "version": 1,
            "capsule_id": capsule_id,
            "default_compartment_id": str(uuid.uuid4()),
            "signing_public_key": b64(public_key_bytes(signing_key)),
            "signing_key_nonce": b64(nonce),
            "signing_key_ciphertext": b64(encrypted_signing_key),
            "export_sequence": 0,
        }
        key_store.set(capsule_id, root_key)
        try:
            _atomic_json(state_path, metadata)
        except Exception:
            key_store.delete(capsule_id)
            raise
        vault = cls(path, metadata, key_store)
        vault._unlock(root_key)
        return vault

    @classmethod
    def open(cls, path: str | Path, *, key_store: KeyStore | None = None) -> SoulVault:
        path = Path(path)
        try:
            metadata = json.loads((path / STATE_FILE).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SoulError("No readable V3 vault exists at this path") from exc
        if metadata.get("format") != "evolving-soul-vault":
            from .errors import UnsupportedLegacyFormat

            raise UnsupportedLegacyFormat()
        key_store = key_store or PlatformKeyring()
        vault = cls(path, metadata, key_store)
        vault._unlock(key_store.get(vault.capsule_id))
        return vault

    def _unlock(self, root_key: bytes) -> None:
        raw = decrypt(
            derive_key(root_key, b"soul-vault/signing-key/v1"),
            unb64(self.metadata["signing_key_nonce"]),
            unb64(self.metadata["signing_key_ciphertext"]),
            self.capsule_id.encode(),
        )
        self._root_key = root_key
        self._signing_key = load_private_key(raw)
        self._store = EncryptedStore(self.path / DATABASE_FILE, root_key)
        self._memory = MemoryRepository(self._store)

    def _require_memory(self) -> MemoryRepository:
        if self._memory is None or self._root_key is None:
            raise VaultLockedError("Vault is locked")
        return self._memory

    def lock(self) -> None:
        if self._store is not None:
            self._store.close()
        self._store = None
        self._memory = None
        self._root_key = None
        self._signing_key = None

    def propose_memory(
        self,
        content: str,
        *,
        provenance: Provenance,
        compartment_id: str | None = None,
    ) -> MemoryProposal:
        return self._require_memory().propose(
            content, compartment_id or self.metadata["default_compartment_id"], provenance
        )

    def list_proposals(self) -> list[MemoryProposal]:
        return self._require_memory().list_proposals()

    def approve_memory(
        self,
        proposal_id: str,
        *,
        actor_credential_id: str,
        edited_content: str | None = None,
        owner_asserted: bool = False,
    ) -> MemoryRecord:
        require_step_up(owner_asserted)
        return self._require_memory().approve(proposal_id, actor_credential_id, edited_content)

    def reject_memory(self, proposal_id: str, *, owner_asserted: bool = False) -> None:
        require_step_up(owner_asserted)
        self._require_memory().reject(proposal_id)

    def search_context(
        self,
        query: str,
        *,
        compartment_ids: set[str] | None = None,
        limit: int = 8,
        token_budget: int = 1_024,
    ) -> list[MemoryRecord]:
        records = self._require_memory().records(compartment_ids)
        return search_bm25(records, query, limit=limit, token_budget=token_budget)

    def export(
        self,
        destination: str | Path,
        *,
        passphrase: str,
        recovery_destination: str | Path | None = None,
    ) -> Path:
        memory = self._require_memory()
        if self._root_key is None or self._signing_key is None:
            raise VaultLockedError("Vault is locked")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in memory.records():
            grouped.setdefault(record.compartment_id, []).append(asdict(record))
        compartments = [
            Compartment(compartment_id=cid, kind="memory", label="Approved memory", records=rows)
            for cid, rows in grouped.items()
        ]
        self.metadata["export_sequence"] = int(self.metadata["export_sequence"]) + 1
        _atomic_json(self.path / STATE_FILE, self.metadata)
        succession = (
            next(self._store.iter_objects("succession-secret"), None) if self._store else None
        )
        recovery_ids = None
        recovery_key = None
        policy_hash = None
        if succession is not None:
            _opaque_id, setup = succession
            recovery_ids = set(setup["compartment_ids"])
            recovery_key = unb64(setup["release_key"])
            policy_hash = setup["policy_hash"]
        return SoulCapsule.export(
            destination,
            capsule_id=self.capsule_id,
            root_key=self._root_key,
            signing_key=self._signing_key,
            compartments=compartments,
            passphrase=passphrase,
            sequence=self.metadata["export_sequence"],
            recovery_destination=recovery_destination,
            recovery_compartment_ids=recovery_ids,
            recovery_key=recovery_key,
            policy_hash=policy_hash,
        )

    @staticmethod
    def verify(source: str | Path, passphrase: str | None = None) -> CapsuleHeader:
        return SoulCapsule.verify(source, passphrase)

    def configure_succession(
        self, policy: SuccessionPolicy, *, owner_asserted: bool = False
    ) -> ReleaseShares:
        require_step_up(owner_asserted)
        store = self._store
        if store is None:
            raise VaultLockedError("Vault is locked")
        # Replacing a policy creates a new opaque object and invalidates previous shares.
        for kind in ("succession-policy", "succession-secret"):
            for opaque_id, _ in list(store.iter_objects(kind)):
                store.delete(opaque_id)
        release_key, shares = create_release_shares()
        policy_hash = __import__("hashlib").sha256(canonical_json(asdict(policy))).hexdigest()
        store.put(
            secrets.token_bytes(24),
            "succession-secret",
            {
                "release_key": b64(release_key),
                "policy_hash": policy_hash,
                "compartment_ids": policy.compartment_ids,
            },
        )
        store.put(secrets.token_bytes(24), "succession-policy", asdict(policy))
        return shares

    def revoke_succession(self, *, owner_asserted: bool = False) -> None:
        require_step_up(owner_asserted)
        store = self._store
        if store is None:
            raise VaultLockedError("Vault is locked")
        for kind in ("succession-policy", "succession-secret"):
            for opaque_id, _ in list(store.iter_objects(kind)):
                store.delete(opaque_id)

    def check_in(self, *, owner_asserted: bool = False) -> dict[str, str]:
        require_step_up(owner_asserted)
        # The coordinator replaces this local receipt with a signed UTC receipt.
        return {"capsule_id": self.capsule_id, "status": "owner-asserted"}
