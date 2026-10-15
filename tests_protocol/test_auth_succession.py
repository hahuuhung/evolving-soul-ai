from datetime import UTC, datetime, timedelta

import pytest

from evolving_soul.auth import BootstrapManager, PairingTokenManager
from evolving_soul.errors import AuthenticationRequired, SuccessionError
from evolving_soul.succession import PolicyRuntime, SuccessionState
from evolving_soul.types import SuccessionPolicy


def test_bootstrap_is_one_time():
    bootstrap = BootstrapManager()
    issued = bootstrap.issue()
    bootstrap.consume(issued.code)
    with pytest.raises(AuthenticationRequired):
        bootstrap.consume(issued.code)


def test_pairing_token_is_user_bound_and_narrow():
    manager = PairingTokenManager(b"x" * 32)
    token = manager.issue("open-webui-user-1")
    assert manager.verify(token, "open-webui-user-1", "context:read")
    with pytest.raises(AuthenticationRequired):
        manager.verify(token, "other-user", "context:read")
    with pytest.raises(AuthenticationRequired):
        manager.verify(token, "open-webui-user-1", "proposal:approve")


def test_coordinator_plus_two_distinct_guardians_after_grace():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = SuccessionPolicy(
        policy_id="policy-1",
        guardian_credential_ids=["g1", "g2", "g3"],
        compartment_ids=["memory-1"],
        inactivity_days=10,
        grace_days=3,
    )
    runtime = PolicyRuntime.create(policy, start)
    during_grace = start + timedelta(days=11)
    runtime.guardian_claim("g1", during_grace)
    runtime.guardian_claim("g2", during_grace)
    assert runtime.state == SuccessionState.GRACE
    after_grace = start + timedelta(days=14)
    assert runtime.evaluate(after_grace) == SuccessionState.QUORUM_READY
    runtime.release(after_grace)
    assert runtime.state == SuccessionState.RELEASED


def test_one_guardian_cannot_release_and_owner_checkin_cancels_claim():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    policy = SuccessionPolicy("p", ["g1", "g2", "g3"], ["c"], 1, 1)
    runtime = PolicyRuntime.create(policy, start)
    eligible = start + timedelta(days=3)
    runtime.guardian_claim("g1", eligible)
    with pytest.raises(SuccessionError):
        runtime.release(eligible)
    runtime.heartbeat(eligible)
    assert runtime.state == SuccessionState.ACTIVE
    assert runtime.guardian_assertions == {}
