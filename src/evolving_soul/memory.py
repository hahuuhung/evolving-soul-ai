"""Owner-approved memory workflow and in-memory lexical retrieval."""

from __future__ import annotations

import math
import re
import secrets
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from .errors import ProposalStateError
from .storage import EncryptedStore
from .types import ConsentReceipt, MemoryProposal, MemoryRecord, Provenance

TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _proposal(value: dict) -> MemoryProposal:
    value = dict(value)
    value["provenance"] = Provenance(**value["provenance"])
    return MemoryProposal(**value)


def _record(value: dict) -> MemoryRecord:
    value = dict(value)
    value["provenance"] = Provenance(**value["provenance"])
    value["consent"] = ConsentReceipt(**value["consent"])
    return MemoryRecord(**value)


class MemoryRepository:
    def __init__(self, store: EncryptedStore) -> None:
        self.store = store

    def propose(self, content: str, compartment_id: str, provenance: Provenance) -> MemoryProposal:
        content = content.strip()
        if not content:
            raise ValueError("A memory proposal cannot be empty")
        now = datetime.now(UTC)
        proposal = MemoryProposal(
            proposal_id=secrets.token_urlsafe(18),
            content=content,
            compartment_id=compartment_id,
            provenance=provenance,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(days=7)).isoformat(),
        )
        self.store.put(secrets.token_bytes(24), "proposal", asdict(proposal))
        return proposal

    def _purge_expired(self) -> None:
        now = datetime.now(UTC)
        for opaque_id, value in list(self.store.iter_objects("proposal")):
            if _parse_time(value["expires_at"]) <= now:
                # Deletion removes rejected/expired content rather than archiving it.
                self.store.delete(opaque_id)

    def list_proposals(self) -> list[MemoryProposal]:
        self._purge_expired()
        return [_proposal(value) for _, value in self.store.iter_objects("proposal")]

    def _find_proposal(self, proposal_id: str) -> tuple[bytes, MemoryProposal]:
        self._purge_expired()
        for opaque_id, value in self.store.iter_objects("proposal"):
            proposal = _proposal(value)
            if secrets.compare_digest(proposal.proposal_id, proposal_id):
                return opaque_id, proposal
        raise ProposalStateError("Proposal is missing, expired, or already decided")

    def approve(
        self, proposal_id: str, actor_credential_id: str, edited_content: str | None = None
    ) -> MemoryRecord:
        opaque_id, proposal = self._find_proposal(proposal_id)
        content = (edited_content if edited_content is not None else proposal.content).strip()
        if not content:
            raise ValueError("Approved memory cannot be empty")
        receipt = ConsentReceipt(action="approved", actor_credential_id=actor_credential_id)
        record = MemoryRecord(
            memory_id=secrets.token_urlsafe(18),
            content=content,
            compartment_id=proposal.compartment_id,
            provenance=proposal.provenance,
            consent=receipt,
            approved_at=receipt.occurred_at,
        )
        self.store.put(secrets.token_bytes(24), "memory", asdict(record))
        self.store.delete(opaque_id)
        return record

    def reject(self, proposal_id: str) -> None:
        opaque_id, _proposal_value = self._find_proposal(proposal_id)
        self.store.delete(opaque_id)

    def records(self, compartment_ids: set[str] | None = None) -> list[MemoryRecord]:
        records = [_record(value) for _, value in self.store.iter_objects("memory")]
        if compartment_ids is not None:
            records = [r for r in records if r.compartment_id in compartment_ids]
        return records


def search_bm25(
    records: Iterable[MemoryRecord], query: str, *, limit: int, token_budget: int
) -> list[MemoryRecord]:
    """Build a transient BM25-style index. No plaintext index reaches disk."""
    records = list(records)
    query_terms = [term.lower() for term in TOKEN_RE.findall(query)]
    if not query_terms or not records:
        return []
    documents = [[t.lower() for t in TOKEN_RE.findall(r.content)] for r in records]
    average_length = sum(map(len, documents)) / max(len(documents), 1)
    frequencies = {term: sum(term in set(doc) for doc in documents) for term in query_terms}
    scored: list[tuple[float, MemoryRecord]] = []
    for record, document in zip(records, documents, strict=True):
        score = 0.0
        for term in query_terms:
            frequency = document.count(term)
            if not frequency:
                continue
            inverse = math.log(
                1 + (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
            )
            denominator = frequency + 1.2 * (0.25 + 0.75 * len(document) / max(average_length, 1))
            score += inverse * frequency * 2.2 / denominator
        if score:
            scored.append((score, record))
    selected: list[MemoryRecord] = []
    used = 0
    for _score, record in sorted(scored, key=lambda item: item[0], reverse=True):
        estimate = max(1, len(record.content) // 4)
        if selected and used + estimate > token_budget:
            continue
        if estimate > token_budget:
            continue
        selected.append(record)
        used += estimate
        if len(selected) >= limit:
            break
    return selected
