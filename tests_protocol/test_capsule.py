import json
import os
import uuid
import zipfile

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

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


def test_rollback_floor_rejects_older_export(tmp_path):
    path, _ = make_capsule(tmp_path)
    with pytest.raises(CapsuleIntegrityError, match="older"):
        SoulCapsule.open(path, "correct horse battery staple", minimum_sequence=2)


def test_tampered_manifest_is_detected_without_passphrase(tmp_path):
    path, _ = make_capsule(tmp_path)
    rewritten = tmp_path / "tampered.soul"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            target.writestr(
                info.filename, b"tampered" if info.filename == "manifest.enc" else source.read(info)
            )
    os.replace(rewritten, path)
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.verify(path)


def test_undeclared_and_unsafe_entries_are_rejected(tmp_path):
    path, _ = make_capsule(tmp_path)
    with zipfile.ZipFile(path, "a") as archive:
        archive.writestr("../escape", b"no")
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.verify(path)


def test_compression_bomb_ratio_is_rejected(tmp_path):
    path = tmp_path / "bomb.soul"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("header.json", b"0" * 100_000)
        archive.writestr("manifest.enc", b"x")
    with pytest.raises(CapsuleIntegrityError, match="compression"):
        SoulCapsule.verify(path)


def test_legacy_marker_returns_typed_error(tmp_path):
    path = tmp_path / "old.enc"
    path.write_text(json.dumps({"owner_profile": {}}))
    with pytest.raises(UnsupportedLegacyFormat):
        SoulCapsule.verify(path)


@settings(max_examples=40, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.binary(max_size=2048))
def test_random_parser_input_fails_with_typed_error(tmp_path, data):
    path = tmp_path / "fuzz.soul"
    path.write_bytes(data)
    with pytest.raises(CapsuleIntegrityError):
        SoulCapsule.verify(path)
