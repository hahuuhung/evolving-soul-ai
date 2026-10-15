"""
Kiểm thử két sắt V3 và bộ chống dò.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import pytest

from evolving_soul.errors import LockedOutError, VaultCorruptError, VaultLockedError, VaultNotFoundError
from evolving_soul.guard import AttemptGuard
from evolving_soul.vault import Vault
from tests.conftest import FAST_KDF_N, PASSPHRASE


@pytest.fixture
def vault(tmp_path) -> Vault:
    return Vault(tmp_path / "vault", kdf_n=FAST_KDF_N)


def test_initialize_unlock_and_profile_roundtrip(vault):
    session = vault.initialize(PASSPHRASE)
    vault.save_profile(session, {"owner_name": "HÀ HỮU HƯNG (1985)", "generation": 1})

    again = Vault(vault.dir, kdf_n=FAST_KDF_N).unlock(PASSPHRASE)
    profile = vault.load_profile(again)
    assert profile["owner_name"] == "HÀ HỮU HƯNG (1985)"
    assert profile["schema_version"] == 3


def test_wrong_passphrase_raises(vault):
    vault.initialize(PASSPHRASE)
    with pytest.raises(VaultLockedError):
        vault.unlock("sai-passphrase")
    with pytest.raises(VaultLockedError):
        vault.unlock(PASSPHRASE.lower())


def test_uninitialized_and_reinitialize(vault):
    with pytest.raises(VaultNotFoundError):
        vault.unlock(PASSPHRASE)
    with pytest.raises(VaultLockedError):
        vault.initialize("ngan")
    vault.initialize(PASSPHRASE)
    with pytest.raises(VaultCorruptError):
        vault.initialize(PASSPHRASE)


def test_no_plaintext_on_disk(vault):
    session = vault.initialize(PASSPHRASE)
    vault.save_profile(session, {"owner_name": "Hà Minh Khôi", "assets": ["MASTER-KEY-8X-2026"]})
    for path in vault.dir.iterdir():
        raw = path.read_bytes()
        assert b"MASTER-KEY" not in raw
        assert "Khôi".encode("utf-8") not in raw
        assert PASSPHRASE.encode("utf-8") not in raw


def test_corrupt_profile_falls_back_to_backup(vault):
    session = vault.initialize(PASSPHRASE)
    vault.save_profile(session, {"generation": 1})
    vault.save_profile(session, {"generation": 2})
    vault.profile_path.write_bytes(b"hong-du-lieu")
    assert vault.load_profile(session)["generation"] == 1

    vault.backup_path.unlink()
    with pytest.raises(VaultCorruptError):
        vault.load_profile(session)


def test_legacy_wrap_unlocks_same_master_key(vault):
    session = vault.initialize(PASSPHRASE)
    vault.save_profile(session, {"generation": 7})
    assert not vault.has_legacy_wrap()

    vault.set_legacy_secret(session, "Kỷ niệm phố cổ Hà Nội")
    kin = vault.unlock_with_legacy_secret("kỷ niệm phố cổ  hà nội")
    assert vault.load_profile(kin)["generation"] == 7
    with pytest.raises(VaultLockedError):
        vault.unlock_with_legacy_secret("sai mat uoc")
    # Phiên của người thân không được đổi khóa
    with pytest.raises(VaultLockedError):
        vault.set_legacy_secret(kin, "chiem quyen")


def test_change_passphrase(vault):
    session = vault.initialize(PASSPHRASE)
    vault.change_passphrase(session, "Passphrase-moi-2027")
    with pytest.raises(VaultLockedError):
        vault.unlock(PASSPHRASE)
    assert vault.unlock("Passphrase-moi-2027").unlocked_by == "owner"


def test_session_repr_hides_key(vault):
    session = vault.initialize(PASSPHRASE)
    assert session.master_key.hex() not in repr(session)


def test_guard_escalating_lockout(tmp_path):
    now = [1000.0]
    guard = AttemptGuard(tmp_path, max_failures=3, base_seconds=60, clock=lambda: now[0])
    for _ in range(2):
        guard.check("owner")
        guard.record_failure("owner")
    guard.record_failure("owner")
    with pytest.raises(LockedOutError) as info:
        guard.check("owner")
    assert info.value.retry_after_seconds == pytest.approx(60)

    now[0] += 61
    guard.check("owner")
    for _ in range(3):
        guard.record_failure("owner")
    with pytest.raises(LockedOutError) as info:
        guard.check("owner")
    assert info.value.retry_after_seconds == pytest.approx(120)  # lần khóa thứ 2 nhân đôi

    guard.check("kin")  # kênh khác không bị ảnh hưởng
    now[0] += 121
    guard.record_success("owner")
    assert guard.failures("owner") == 0
