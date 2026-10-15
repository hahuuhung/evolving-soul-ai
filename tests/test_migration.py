"""
Kiểm thử migration két sắt V2 -> V3.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from evolving_soul import legacy_v2
from evolving_soul.engine import EvolvingSoulEngine
from evolving_soul.errors import ProfileExistsError, VaultLockedError
from tests.conftest import PASSPHRASE
from tests.test_engine_owner import STRANGER, FakeClock
from tests.test_features import DEVICE, OWNER


def write_v2_vault(vault_dir: Path, data: dict, phrase: str = legacy_v2.V2_DEFAULT_PHRASE, with_legacy: bool = True) -> Path:
    """Tạo két sắt đúng định dạng V2 (như core_engine.EvolvingOwnerAI_V2.register_owner + setup_digital_legacy)."""
    vec, family, words = legacy_v2._package(data)
    profile = {
        "owner_name": data.get("owner_name", "HÀ HỮU HƯNG (1985)"),
        "evolving_vector": vec.tolist(),
        "family_hashes": [legacy_v2._hash_norm(w) for w in family],
        "cognitive_keywords": list(words),
        "traits_saved": data.get("traits", []),
        "radar_baseline": {},
        "generation": 4,
        "created_at": "2026-01-01 08:00:00",
    }
    if with_legacy:
        profile["legacy_config"] = {
            "heir_name_display": "Hà Minh Khôi",
            "heir_name_hash": legacy_v2._hash_norm("Hà Minh Khôi"),
            "family_secret_hash": legacy_v2._hash_norm("bi mat"),
            "inactivity_threshold_days": 730,
            "digital_assets": ["MASTER-KEY-8X-2026"],
            "legacy_message": "Giữ vững đạo đức nghề nghiệp.",
        }
    key = base64.urlsafe_b64encode(hashlib.sha256(phrase.encode("utf-8")).digest())
    vault_dir.mkdir(parents=True, exist_ok=True)
    path = vault_dir / legacy_v2.V2_FILE
    path.write_bytes(Fernet(key).encrypt(json.dumps(profile).encode("utf-8")))
    return path


def make(settings) -> EvolvingSoulEngine:
    return EvolvingSoulEngine(settings, clock=FakeClock(), device_probe=lambda: DEVICE)


def test_read_v2_with_wrong_phrase(tmp_path):
    path = write_v2_vault(tmp_path, OWNER, phrase="cum-tu-rieng")
    with pytest.raises(VaultLockedError):
        legacy_v2.read_v2_profile(path)
    assert legacy_v2.read_v2_profile(path, "cum-tu-rieng")["generation"] == 4


def test_full_migration_flow(settings):
    write_v2_vault(settings.vault_dir, OWNER)
    eng = make(settings)
    assert eng.needs_migration

    eng.migrate_from_v2(PASSPHRASE)
    assert not eng.needs_migration and eng.migration_pending
    assert not eng.v2_vault_path.exists() and eng.v2_backup_path.exists()
    with pytest.raises(ProfileExistsError):
        eng.register_owner(OWNER)  # không ai đăng ký chen ngang được trong lúc chờ migrate

    # Kẻ lạ không hoàn tất được migration
    assert not eng.verify_owner(STRANGER)["is_owner"]
    assert eng.migration_pending

    res = eng.verify_owner(OWNER)
    assert res["is_owner"] and res["migrated"]
    assert res["generation"] == 5  # giữ lịch sử thế hệ V2 + 1
    assert not eng.migration_pending
    assert not eng.v2_backup_path.exists()  # file khóa công khai đã bị xóa

    profile = eng.profile
    assert "v2_profile" not in profile and len(profile["model"]["vector"]) == 14
    assert profile["legacy_v2_pending"]["assets"] == ["MASTER-KEY-8X-2026"]

    # Từ đây dùng thuật toán V3 bình thường, mở lại bằng passphrase mới
    other = make(settings)
    other.unlock(PASSPHRASE)
    nxt = other.verify_owner(OWNER)
    assert nxt["is_owner"] and not nxt["migrated"] and nxt["generation"] == 6
    assert [e["event"] for e in other.audit_events()][:3] == ["vault_created", "migration_started", "owner_verification"]


def test_migration_with_custom_v2_phrase_and_no_legacy(settings):
    write_v2_vault(settings.vault_dir, OWNER, phrase="cum-tu-rieng", with_legacy=False)
    eng = make(settings)
    with pytest.raises(VaultLockedError):
        eng.migrate_from_v2(PASSPHRASE)
    assert not eng.is_initialized  # thất bại không để lại két V3 dở dang
    eng.migrate_from_v2(PASSPHRASE, v2_phrase="cum-tu-rieng")
    assert eng.verify_owner(OWNER)["is_owner"]
    assert eng.profile["legacy_v2_pending"] is None


def test_cannot_migrate_twice(settings):
    write_v2_vault(settings.vault_dir, OWNER)
    eng = make(settings)
    eng.migrate_from_v2(PASSPHRASE)
    write_v2_vault(settings.vault_dir, OWNER)
    with pytest.raises(ProfileExistsError):
        eng.migrate_from_v2(PASSPHRASE)


def test_v3_vault_has_no_v2_plaintext_after_migration(settings):
    write_v2_vault(settings.vault_dir, OWNER)
    eng = make(settings)
    eng.migrate_from_v2(PASSPHRASE)
    eng.verify_owner(OWNER)
    for path in settings.vault_dir.iterdir():
        raw = path.read_bytes()
        for secret in [b"MASTER-KEY", "Khôi".encode("utf-8"), b"1985-05-15"]:
            assert secret not in raw, f"{secret!r} lộ trong {path.name}"
