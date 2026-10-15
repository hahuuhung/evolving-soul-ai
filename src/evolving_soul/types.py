"""Stable, serializable V3 protocol types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class CapsuleHeader:
    magic: str
    format_version: str
    capsule_id: str
    created_at: str
    crypto_suite: str
    signing_public_key: str
    manifest_entry: str
    manifest_nonce: str
    manifest_sha256: str
    signature: str
    key_wrap: dict[str, Any]


@dataclass(slots=True)
class Compartment:
    compartment_id: str
    kind: str
    label: str
    records: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CapsuleManifest:
    capsule_id: str
    format_version: str
    created_at: str
    compartments: list[dict[str, Any]]
    sequence: int = 1


@dataclass(slots=True)
class Provenance:
    source: str
    captured_at: str = field(default_factory=lambda: utc_now().isoformat())
    extractor: str = "rule-based-local"
    source_ref: str | None = None


@dataclass(slots=True)
class ConsentReceipt:
    action: Literal["approved", "rejected"]
    actor_credential_id: str
    occurred_at: str = field(default_factory=lambda: utc_now().isoformat())
    policy_version: str = "1"


@dataclass(slots=True)
class MemoryProposal:
    proposal_id: str
    content: str
    compartment_id: str
    provenance: Provenance
    created_at: str
    expires_at: str
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"


@dataclass(slots=True)
class MemoryRecord:
    memory_id: str
    content: str
    compartment_id: str
    provenance: Provenance
    consent: ConsentReceipt
    approved_at: str


@dataclass(slots=True)
class SuccessionPolicy:
    policy_id: str
    guardian_credential_ids: list[str]
    compartment_ids: list[str]
    inactivity_days: int = 730
    grace_days: int = 30
    version: int = 1
    revoked: bool = False


@dataclass(slots=True)
class AuditEvent:
    event_id: str
    event_type: str
    occurred_at: str
    actor: str
    details: dict[str, Any] = field(default_factory=dict)


def to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)
