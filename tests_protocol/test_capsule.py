import json
import uuid
import zipfile

import pytest

from evolving_soul.capsule import SoulCapsule
from evolving_soul.crypto import new_signing_key, random_key
from evolving_soul.errors import CapsuleIntegrityError, UnsupportedLegacyFormat
from evolving_soul.types import Compartment


def make_capsule(tmp_path):
    path = tmp_path / "memory.soul"
    cid = str(uuid.uuid4())
    compartments = [
        Compartment(str(uuid.uuid4()), "memory", "Personal", [{"content": "tea"}]),
        Compartment(str(uuid.uuid4()), "memory", "Work", [{"content": "Python"}]),
    ]
    SoulCapsule.export(
        path,
        capsule_id=cid,
        root_key=random_key(),
        signing_key=new_signing_key(),
        compartments=compartments,
        passphrase="correct horse battery staple",
    )
    return path, cid


def test_round_trip_and_independent_nonces(tmp_path):
    path, cid = make_capsule(tmp_path)
    header, manifest, compartments, root_key = SoulCapsule.open(
        path, "correct horse battery staple"
    )
    assert header.capsule_id == cid
    assert manifest is not None and manifest.format_version == "1.0"
    assert root_key is not None
    assert {item.label for item in compartments} == {"Personal", "Work"}
    with zipfile.ZipFile(path) as archive:
        nonces = [archive.read(item["entry"])[:12] for item in manifest.compartments]
    assert len(nonces) == len(set(nonces))


def test_wrong_passphrase_fails_closed(tmp_path):
    path, _ = make_capsule(tmp_path)
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.open(path, "wrong")


def test_tampered_manifest_is_detected_without_passphrase(tmp_path):
    path, _ = make_capsule(tmp_path)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("manifest.enc", b"tampered")
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.verify(path)


def test_undeclared_and_unsafe_entries_are_rejected(tmp_path):
    path, _ = make_capsule(tmp_path)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("../escape", b"no")
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.verify(path)


def test_legacy_marker_returns_typed_error(tmp_path):
    path = tmp_path / "old.enc"
    path.write_text(json.dumps({"owner_profile": {}}))
    with pytest.raises(UnsupportedLegacyFormat):
        SoulCapsule.verify(path)
