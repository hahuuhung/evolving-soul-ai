import uuid

import pytest
from shamir_mnemonic import MnemonicError, combine_mnemonics

from evolving_soul.capsule import SoulCapsule
from evolving_soul.crypto import new_signing_key, random_key
from evolving_soul.errors import CapsuleIntegrityError
from evolving_soul.recovery import recover_compartments
from evolving_soul.succession import create_release_shares
from evolving_soul.types import Compartment


def test_slip39_requires_coordinator_and_two_guardians():
    release_key, shares = create_release_shares()
    guardians = shares.guardian_mnemonics
    coordinator = shares.coordinator_mnemonic

    with pytest.raises(MnemonicError):
        combine_mnemonics(guardians)
    with pytest.raises(MnemonicError):
        combine_mnemonics([coordinator, guardians[0]])
    assert combine_mnemonics([coordinator, guardians[0], guardians[1]]) == release_key


def test_recovery_bundle_opens_only_selected_compartment(tmp_path):
    release_key, _shares = create_release_shares()
    selected_id = str(uuid.uuid4())
    excluded_id = str(uuid.uuid4())
    capsule = tmp_path / "capsule.soul"
    bundle = tmp_path / "recovery.soul-recovery"
    SoulCapsule.export(
        capsule,
        capsule_id=str(uuid.uuid4()),
        root_key=random_key(),
        signing_key=new_signing_key(),
        compartments=[
            Compartment(selected_id, "memory", "Selected", [{"secret": "selected"}]),
            Compartment(excluded_id, "memory", "Excluded", [{"secret": "excluded"}]),
        ],
        passphrase="test export passphrase",  # noqa: S106
        recovery_destination=bundle,
        recovery_compartment_ids={selected_id},
        recovery_key=release_key,
        policy_hash="policy-v1",
    )
    recovered = recover_compartments(capsule, bundle, release_key)
    assert [item.compartment_id for item in recovered] == [selected_id]
    assert b"selected" not in bundle.read_bytes()
    assert b"excluded" not in bundle.read_bytes()
    with pytest.raises(CapsuleIntegrityError):
        recover_compartments(capsule, bundle, random_key())


def test_rotated_policy_shares_do_not_mix():
    _old_key, old = create_release_shares()
    _new_key, new = create_release_shares()
    with pytest.raises(MnemonicError):
        combine_mnemonics(
            [
                old.coordinator_mnemonic,
                new.guardian_mnemonics[0],
                new.guardian_mnemonics[1],
            ]
        )
