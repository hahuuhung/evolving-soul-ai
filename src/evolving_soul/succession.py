"""Coordinator-authoritative succession state machine and SLIP-39 split."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from .errors import SuccessionError
from .types import SuccessionPolicy


class SuccessionState(StrEnum):
    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    QUORUM_READY = "QUORUM_READY"
    RELEASED = "RELEASED"
    REVOKED = "REVOKED"


@dataclass(slots=True)
class PolicyRuntime:
    policy: SuccessionPolicy
    policy_hash: str
    last_heartbeat: datetime
    state: SuccessionState = SuccessionState.ACTIVE
    guardian_assertions: dict[str, datetime] = field(default_factory=dict)
    released_at: datetime | None = None

    @classmethod
    def create(cls, policy: SuccessionPolicy, coordinator_now: datetime) -> "PolicyRuntime":
        if len(set(policy.guardian_credential_ids)) != 3:
            raise SuccessionError("A policy requires three distinct guardian credentials")
        if not policy.compartment_ids:
            raise SuccessionError("A policy must select at least one compartment")
        digest = hashlib.sha256(repr(policy).encode()).hexdigest()
        return cls(policy=policy, policy_hash=digest, last_heartbeat=coordinator_now)

    def evaluate(self, coordinator_now: datetime) -> SuccessionState:
        if self.state in {SuccessionState.REVOKED, SuccessionState.RELEASED}:
            return self.state
        inactive_at = self.last_heartbeat + timedelta(days=self.policy.inactivity_days)
        release_eligible_at = inactive_at + timedelta(days=self.policy.grace_days)
        if coordinator_now < inactive_at:
            self.state = SuccessionState.ACTIVE
        elif coordinator_now < release_eligible_at:
            self.state = SuccessionState.GRACE
        elif len(self.guardian_assertions) >= 2:
            self.state = SuccessionState.QUORUM_READY
        else:
            self.state = SuccessionState.GRACE
        return self.state

    def heartbeat(self, coordinator_now: datetime) -> None:
        if self.state == SuccessionState.RELEASED:
            raise SuccessionError("A released policy cannot be reactivated")
        self.last_heartbeat = coordinator_now
        self.guardian_assertions.clear()
        self.state = SuccessionState.ACTIVE

    def guardian_claim(self, credential_id: str, coordinator_now: datetime) -> None:
        if credential_id not in self.policy.guardian_credential_ids:
            raise SuccessionError("Credential is not a guardian for this policy")
        if self.evaluate(coordinator_now) == SuccessionState.ACTIVE:
            raise SuccessionError("A claim cannot start before the inactivity threshold")
        self.guardian_assertions[credential_id] = coordinator_now
        self.evaluate(coordinator_now)

    def release(self, coordinator_now: datetime) -> None:
        if self.evaluate(coordinator_now) != SuccessionState.QUORUM_READY:
            raise SuccessionError("Coordinator and two guardians are not release-eligible")
        self.state = SuccessionState.RELEASED
        self.released_at = coordinator_now

    def revoke(self) -> None:
        self.guardian_assertions.clear()
        self.state = SuccessionState.REVOKED


@dataclass(slots=True)
class ReleaseShares:
    guardian_mnemonics: list[list[str]]
    coordinator_mnemonic: str


def create_release_shares(release_key: bytes | None = None) -> tuple[bytes, ReleaseShares]:
    """Create top-level 2-of-2 groups: guardians 2-of-3 and coordinator 1-of-1."""
    try:
        from shamir_mnemonic import generate_mnemonics
    except ImportError as exc:
        raise SuccessionError(
            "SLIP-39 support requires evolving-soul-ai[coordinator]"
        ) from exc
    release_key = release_key or secrets.token_bytes(32)
    groups = generate_mnemonics(
        group_threshold=2,
        groups=[(2, 3), (1, 1)],
        master_secret=release_key,
        passphrase=b"",
        iteration_exponent=1,
    )
    return release_key, ReleaseShares(guardian_mnemonics=groups[0], coordinator_mnemonic=groups[1][0])


def utc_now() -> datetime:
    return datetime.now(UTC)
