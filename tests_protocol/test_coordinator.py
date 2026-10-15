from datetime import UTC, datetime, timedelta

import pytest

from evolving_soul.coordinator import CoordinatorService, InMemoryCoordinatorRepository
from evolving_soul.errors import AuthenticationRequired, SuccessionError
from evolving_soul.types import SuccessionPolicy


class FakeVerifier:
    def verify(self, credential, response, challenge):
        assert response["challenge"] == challenge.hex()
        return int(credential["sign_count"]) + 1


def assertion(service, capsule_id, actor):
    issued = service.challenge(capsule_id, actor)
    from evolving_soul.crypto import unb64

    return issued["challenge_id"], {"challenge": unb64(issued["challenge"]).hex()}


def configured_service():
    repository = InMemoryCoordinatorRepository()
    service = CoordinatorService(repository, deployment_key=b"d" * 32, verifier=FakeVerifier())
    policy = SuccessionPolicy("p1", ["g1", "g2", "g3"], ["selected"], 1, 1)
    pseudonym = service.provision(
        capsule_id="capsule-public-id",
        policy=policy,
        policy_hash="policy-hash",
        owner_credential={"credential_id": "owner", "sign_count": 0},
        guardian_credentials={
            name: {"credential_id": name, "sign_count": 0}
            for name in policy.guardian_credential_ids
        },
        notification_target="owner@example.invalid",
        coordinator_share="coordinator mnemonic words",
    )
    record = repository.get(pseudonym)
    record.runtime.last_heartbeat = datetime.now(UTC) - timedelta(days=3)
    repository.put(record)
    return service, repository


def test_release_requires_two_guardians_and_returns_only_coordinator_share():
    service, _ = configured_service()
    cid = "capsule-public-id"
    challenge_id, response = assertion(service, cid, "g1")
    record = service.assert_actor(
        capsule_id=cid,
        actor="g1",
        challenge_id=challenge_id,
        response=response,
    )
    service.claim(record, "g1")
    with pytest.raises(SuccessionError):
        service.release(cid)

    challenge_id, response = assertion(service, cid, "g2")
    record = service.assert_actor(
        capsule_id=cid,
        actor="g2",
        challenge_id=challenge_id,
        response=response,
    )
    service.claim(record, "g2")
    released = service.release(cid)
    assert released["coordinator_share"] == "coordinator mnemonic words"
    assert "memory" not in str(released).lower()


def test_coordinator_challenge_is_single_use():
    service, _ = configured_service()
    challenge_id, response = assertion(service, "capsule-public-id", "owner")
    service.assert_actor(
        capsule_id="capsule-public-id",
        actor="owner",
        challenge_id=challenge_id,
        response=response,
    )
    with pytest.raises(AuthenticationRequired):
        service.assert_actor(
            capsule_id="capsule-public-id",
            actor="owner",
            challenge_id=challenge_id,
            response=response,
        )
