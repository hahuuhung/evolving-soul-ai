"""
Kiểm thử luồng Chủ nhân của EvolvingSoulEngine: két sắt, đăng ký, xác minh, tiến hóa, chống dò.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import pytest

from evolving_soul.engine import EvolvingSoulEngine
from evolving_soul.errors import LockedOutError, OwnerNotVerifiedError, ProfileExistsError, VaultLockedError
from tests.conftest import PASSPHRASE
from tests.test_features import DEVICE, OWNER

STRANGER = {"dob": "1995-01-01", "family": "Không rõ", "traits": ["Ưa mạo hiểm"], "password": "123456password",
            "answer": "Tôi thích đi du lịch biển và chơi game thâu đêm."}


class FakeClock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t


def make_engine(settings, clock=None) -> EvolvingSoulEngine:
    return EvolvingSoulEngine(settings, clock=clock or FakeClock(), device_probe=lambda: DEVICE)


@pytest.fixture
def engine(settings) -> EvolvingSoulEngine:
    eng = make_engine(settings)
    eng.create_vault(PASSPHRASE)
    eng.register_owner(dict(OWNER, owner_name="HÀ HỮU HƯNG (1985)"))
    return eng


def test_operations_require_unlocked_vault(settings):
    eng = make_engine(settings)
    with pytest.raises(VaultLockedError):
        eng.register_owner(OWNER)
    eng.create_vault(PASSPHRASE)
    eng.lock()
    with pytest.raises(VaultLockedError):
        eng.verify_owner(OWNER)


def test_register_then_verify_evolves_generation(engine, settings):
    assert engine.profile["generation"] == 1
    assert not engine.owner_verified

    res = engine.verify_owner(OWNER)
    assert res["is_owner"] and res["generation"] == 2
    assert engine.owner_verified

    # Mở lại bằng instance mới: hồ sơ đã tiến hóa được lưu bền vững
    other = make_engine(settings)
    other.unlock(PASSPHRASE)
    assert other.profile["generation"] == 2
    assert not other.owner_verified  # trạng thái xác minh không được chia sẻ giữa các phiên


def test_stranger_rejected_without_evolving(engine):
    res = engine.verify_owner(STRANGER)
    assert not res["is_owner"]
    assert res["generation"] == 1
    assert not engine.owner_verified
    assert engine.profile["trust_history"][-1]["is_owner"] is False


def test_cannot_overwrite_profile_without_verification(engine):
    with pytest.raises(ProfileExistsError):
        engine.register_owner(dict(STRANGER, owner_name="HACKER"))
    with pytest.raises(OwnerNotVerifiedError):
        engine.register_owner(dict(STRANGER, owner_name="HACKER"), force=True)
    assert engine.profile["owner_name"] == "HÀ HỮU HƯNG (1985)"

    engine.verify_owner(OWNER)
    engine.register_owner(dict(OWNER, owner_name="Chủ nhân mới"), force=True)
    assert engine.profile["owner_name"] == "Chủ nhân mới"
    assert engine.profile["generation"] == 1


def test_owner_session_expires(settings):
    clock = FakeClock()
    eng = make_engine(settings, clock)
    eng.create_vault(PASSPHRASE)
    eng.register_owner(OWNER)
    eng.verify_owner(OWNER)
    assert eng.owner_verified
    clock.t += settings.owner_session_ttl_seconds + 1
    assert not eng.owner_verified


def test_lockout_after_repeated_failures(engine, settings):
    for _ in range(settings.max_failed_attempts):
        engine.verify_owner(STRANGER)
    with pytest.raises(LockedOutError):
        engine.verify_owner(OWNER)  # kể cả Chủ nhân thật cũng phải chờ hết thời gian khóa


def test_wrong_passphrase_counts_toward_unlock_lockout(engine, settings):
    eng = make_engine(settings)
    for _ in range(settings.max_failed_attempts):
        with pytest.raises(VaultLockedError):
            eng.unlock("sai-passphrase")
    with pytest.raises(LockedOutError):
        eng.unlock(PASSPHRASE)


def test_demo_offset_requires_demo_mode(engine, demo_settings):
    with pytest.raises(PermissionError):
        engine.set_demo_offset_days(800)
    demo = make_engine(demo_settings)
    demo.set_demo_offset_days(800)
    assert demo.now() - demo._clock() == pytest.approx(800 * 86400)


def test_vault_files_have_no_plaintext(engine, settings):
    engine.verify_owner(OWNER)
    for path in settings.vault_dir.iterdir():
        raw = path.read_bytes()
        for secret in ["1985-05-15", "Khôi", "HungAI", "hahuuhung1985", PASSPHRASE]:
            assert secret.encode("utf-8") not in raw, f"{secret} lộ trong {path.name}"
