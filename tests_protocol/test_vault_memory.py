from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from evolving_soul.errors import AuthenticationRequired, ProposalStateError, VaultLockedError
from evolving_soul.keyring_store import MemoryKeyStore
from evolving_soul.types import Provenance
from evolving_soul.vault import SoulVault


def test_proposals_require_owner_action_and_round_trip(tmp_path: Path):
    keys = MemoryKeyStore()
    vault = SoulVault.create(tmp_path / "vault", key_store=keys)
    proposal = vault.propose_memory(
        "The owner prefers concise answers",
        provenance=Provenance(source="open-webui:test"),
    )
    assert vault.search_context("concise") == []
    with pytest.raises(AuthenticationRequired):
        vault.approve_memory(proposal.proposal_id, actor_credential_id="passkey-1")
    record = vault.approve_memory(
        proposal.proposal_id,
        actor_credential_id="passkey-1",
        owner_asserted=True,
    )
    assert record.consent.action == "approved"
    assert vault.search_context("concise")[0].memory_id == record.memory_id

    exported = vault.export(tmp_path / "backup", passphrase="a very long export passphrase")
    assert SoulVault.verify(exported).format_version == "1.0"
    vault.lock()
    with pytest.raises(VaultLockedError):
        vault.search_context("concise")

    reopened = SoulVault.open(tmp_path / "vault", key_store=keys)
    assert reopened.search_context("concise")[0].memory_id == record.memory_id
    reopened.lock()


def test_rejection_erases_proposal(tmp_path: Path):
    vault = SoulVault.create(tmp_path / "vault", key_store=MemoryKeyStore())
    proposal = vault.propose_memory("discard me", provenance=Provenance(source="test"))
    vault.reject_memory(proposal.proposal_id, owner_asserted=True)
    assert vault.list_proposals() == []
    with pytest.raises(ProposalStateError):
        vault.reject_memory(proposal.proposal_id, owner_asserted=True)
    vault.lock()


def test_sqlite_does_not_contain_plaintext(tmp_path: Path):
    vault = SoulVault.create(tmp_path / "vault", key_store=MemoryKeyStore())
    vault.propose_memory("unique plaintext canary", provenance=Provenance(source="test"))
    assert b"unique plaintext canary" not in (tmp_path / "vault" / "objects.sqlite3").read_bytes()
    vault.lock()


def test_concurrent_proposal_writes_are_serialized(tmp_path: Path):
    vault = SoulVault.create(tmp_path / "vault", key_store=MemoryKeyStore())
    with ThreadPoolExecutor(max_workers=4) as executor:
        proposals = list(
            executor.map(
                lambda index: vault.propose_memory(
                    f"remember that synthetic value {index}",
                    provenance=Provenance(source="concurrency-test"),
                ),
                range(20),
            )
        )
    assert len({item.proposal_id for item in proposals}) == 20
    assert len(vault.list_proposals()) == 20
    vault.lock()


def test_expired_proposal_content_is_deleted(tmp_path: Path):
    vault = SoulVault.create(tmp_path / "vault", key_store=MemoryKeyStore())
    proposal = vault.propose_memory("expire this canary", provenance=Provenance(source="test"))
    assert vault._store is not None
    opaque_id, value = next(vault._store.iter_objects("proposal"))
    assert value["proposal_id"] == proposal.proposal_id
    value["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    vault._store.put(opaque_id, "proposal", value)
    assert vault.list_proposals() == []
    vault.lock()
