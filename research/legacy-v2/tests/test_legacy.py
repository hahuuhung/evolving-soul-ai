"""
Kiểm thử Di sản Số (Dead Man's Switch 730 ngày) và nhật ký kiểm toán.
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import json

import cv2
import pytest

from evolving_soul.biometrics import FaceBiometrics, fetch_verified
from evolving_soul.engine import EvolvingSoulEngine
from evolving_soul.errors import LockedOutError, OwnerNotVerifiedError
from tests.conftest import PASSPHRASE
from tests.test_biometrics import MODEL_CACHE, SAMPLES, encode, synthetic_face_bytes
from tests.test_engine_owner import FakeClock
from tests.test_features import DEVICE, OWNER

SECRET = "Kỷ niệm ngôi nhà phố cổ Hà Nội 1985"
ASSETS = ["Bản quyền Evolving Soul AI - HÀ HỮU HƯNG (1985)", "MASTER-KEY-8X-2026"]
SEAL = dict(heir_name="Hà Minh Khôi", heir_email="khoi.ha@gmail.com", family_secret=SECRET, assets=ASSETS,
            message="Con hãy giữ vững đạo đức nghề nghiệp.")
KIN = dict(kin_name="Ha Minh Khoi", kin_email="khoi.ha@gmail.com", owner_dob="1985-05-15",
           family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C", family_secret=SECRET.lower())


def make(settings, clock=None, bio=None) -> EvolvingSoulEngine:
    return EvolvingSoulEngine(settings, clock=clock or FakeClock(), device_probe=lambda: DEVICE,
                              biometrics=bio or FaceBiometrics(settings.model_dir, allow_download=False))


@pytest.fixture
def owner(demo_settings) -> EvolvingSoulEngine:
    eng = make(demo_settings)
    eng.create_vault(PASSPHRASE)
    eng.register_owner(dict(OWNER, owner_name="HÀ HỮU HƯNG (1985)"))
    eng.verify_owner(OWNER)
    return eng


def kin_portal(settings, days_offline: float = 0.0, bio=None) -> EvolvingSoulEngine:
    """Cổng tiếp quản: một instance riêng, KHÔNG có passphrase của Chủ nhân."""
    eng = make(settings, bio=bio)
    if days_offline:
        eng.set_demo_offset_days(days_offline)
    return eng


# =========================================================================
# NIÊM PHONG
# =========================================================================

def test_seal_requires_verified_owner_and_strong_secret(demo_settings):
    eng = make(demo_settings)
    eng.create_vault(PASSPHRASE)
    eng.register_owner(OWNER)
    with pytest.raises(OwnerNotVerifiedError):
        eng.seal_legacy(**SEAL)
    eng.verify_owner(OWNER)
    with pytest.raises(ValueError):
        eng.seal_legacy(**dict(SEAL, family_secret="ngan"))
    status = eng.seal_legacy(**SEAL)
    assert status["threshold_days"] == 730
    assert status["asset_count"] == 2 and not status["has_biometric_lock"]


def test_assets_unreadable_with_owner_passphrase_alone(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    profile_json = json.dumps(owner.profile, ensure_ascii=False)
    assert "MASTER-KEY" not in profile_json
    assert "đạo đức" not in profile_json
    for path in demo_settings.vault_dir.iterdir():
        raw = path.read_bytes()
        for secret in [b"MASTER-KEY", SECRET.encode("utf-8"), "Khôi".encode("utf-8"), b"khoi.ha"]:
            assert secret not in raw, f"{secret!r} lộ trong {path.name}"


# =========================================================================
# CỔNG TIẾP QUẢN
# =========================================================================

def test_before_threshold_kin_is_verified_but_assets_stay_locked(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    res = kin_portal(demo_settings, days_offline=100).claim_legacy(**KIN)
    assert res["is_verified"] and not res["is_unlockable"] and not res["is_unlocked"]
    assert res["assets"] == [] and res["message"] == ""
    assert res["knowledge_score"] == pytest.approx(1.0)


def test_after_threshold_kin_receives_assets_then_owner_return_revokes(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    res = kin_portal(demo_settings, days_offline=735).claim_legacy(**KIN)
    assert res["is_unlocked"]
    assert res["assets"] == ASSETS
    assert "đạo đức" in res["message"]
    assert res["owner_name"] == "HÀ HỮU HƯNG (1985)"

    owner.set_demo_offset_days(735)
    assert owner.legacy_status()["claimed"] is True  # owner thấy trạng thái mới (đọc lại từ đĩa)
    owner.verify_owner(OWNER)  # Chủ nhân quay lại
    status = owner.legacy_status()
    assert status["claimed"] is False and status["elapsed_days"] == 0.0


def test_warning_state_near_threshold(owner):
    owner.seal_legacy(**SEAL)
    owner.set_demo_offset_days(660)
    status = owner.legacy_status()
    assert status["warning"] and not status["is_unlockable"]
    assert status["remaining_days"] == pytest.approx(70.0)


def test_wrong_secret_denied_and_locks_out(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    portal = kin_portal(demo_settings, days_offline=800)
    for _ in range(demo_settings.max_failed_attempts):
        res = portal.claim_legacy(**dict(KIN, family_secret="sai mat uoc roi"))
        assert not res["is_verified"] and res["reason"]
    with pytest.raises(LockedOutError):
        portal.claim_legacy(**KIN)


def test_without_biometrics_knowledge_must_reach_85_percent(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    res = kin_portal(demo_settings, days_offline=800).claim_legacy(**dict(KIN, kin_email="sai@gmail.com"))
    assert res["knowledge_score"] == pytest.approx(0.80)
    assert not res["is_verified"] and not res["is_unlocked"]


def test_simulation_ignored_outside_demo(owner, settings):
    owner.seal_legacy(**SEAL)
    portal = make(settings)  # cùng két sắt, không ở chế độ demo
    with pytest.raises(PermissionError):
        portal.set_demo_offset_days(800)
    assert not portal.claim_legacy(**KIN)["is_unlocked"]


def test_low_assurance_histogram_requires_higher_knowledge(owner, demo_settings):
    owner.seal_legacy(**SEAL, heir_images=[synthetic_face_bytes(100)])
    assert owner.legacy_status()["biometric_method"] == "histogram"
    portal = kin_portal(demo_settings, days_offline=800)

    res = portal.claim_legacy(**KIN, live_image=synthetic_face_bytes(100))
    assert res["bio"]["assurance"] == "low" and res["is_unlocked"]


def test_biometric_lock_requires_live_scan(owner, demo_settings):
    owner.seal_legacy(**SEAL, heir_images=[synthetic_face_bytes(100)])
    res = kin_portal(demo_settings, days_offline=800).claim_legacy(**KIN)
    assert not res["is_verified"]
    assert "sinh trắc" in res["reason"]


@pytest.mark.models
def test_sface_heir_unlocks_and_other_person_rejected(owner, demo_settings):
    bio = FaceBiometrics(MODEL_CACHE)
    if bio.method != "sface":
        pytest.skip("Không có model YuNet/SFace")
    paths = {n: fetch_verified(s, MODEL_CACHE / "samples") for n, s in SAMPLES.items()}
    if not all(paths.values()):
        pytest.skip("Không có ảnh mẫu")
    heir, other = cv2.imread(str(paths["lena.jpg"])), cv2.imread(str(paths["messi5.jpg"]))

    owner.biometrics = bio
    owner.seal_legacy(**SEAL, heir_images=[encode(heir)])
    portal = kin_portal(demo_settings, days_offline=800, bio=bio)

    impostor = portal.claim_legacy(**KIN, live_image=encode(other))
    assert impostor["bio"]["assurance"] == "high" and not impostor["is_unlocked"]
    real = portal.claim_legacy(**KIN, live_image=encode(cv2.flip(heir, 1)))
    assert real["is_unlocked"] and real["bio"]["passed"]


def test_reinitializing_owner_destroys_legacy_wrap(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    owner.register_owner(OWNER, force=True)
    res = kin_portal(demo_settings, days_offline=800).claim_legacy(**KIN)
    assert not res["is_verified"] and res["reason"]


# =========================================================================
# NHẬT KÝ KIỂM TOÁN
# =========================================================================

def test_audit_log_records_events_and_detects_tampering(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    kin_portal(demo_settings, days_offline=10).claim_legacy(**dict(KIN, family_secret="sai mat uoc roi"))
    events = [e["event"] for e in owner.audit_events(50)]
    assert events[:3] == ["vault_created", "owner_registered", "owner_verification"]
    assert "legacy_sealed" in events and events[-1] == "legacy_claim"
    assert owner.audit_integrity()["ok"]

    log = demo_settings.vault_dir / "audit.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[2])
    tampered["result"] = "ok_gia_mao"
    lines[2] = json.dumps(tampered, ensure_ascii=False)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert owner.audit_integrity() == {"ok": False, "broken_at": 2, "entries": 2}

    log.unlink()  # xóa toàn bộ nhật ký -> neo trong hồ sơ không còn khớp
    assert owner.audit_integrity()["reason"] == "anchor_missing"


def test_audit_log_has_no_sensitive_values(owner, demo_settings):
    owner.seal_legacy(**SEAL)
    kin_portal(demo_settings, days_offline=800).claim_legacy(**KIN)
    text = (demo_settings.vault_dir / "audit.jsonl").read_text(encoding="utf-8")
    for secret in ["Khôi", "Khoi", "khoi.ha", "1985-05-15", "MASTER-KEY", SECRET]:
        assert secret not in text


@pytest.mark.parametrize("knowledge, bio, has_lock, expected", [
    (0.75, {"assurance": "high", "passed": True}, True, True),
    (0.65, {"assurance": "high", "passed": True}, True, False),   # tri thức < 70%
    (0.95, {"assurance": "high", "passed": False}, True, False),  # sinh trắc không khớp
    (0.80, {"assurance": "low", "passed": True}, True, False),    # histogram cần ≥ 85%
    (0.90, {"assurance": "low", "passed": True}, True, True),
    (0.95, None, True, False),                                     # có khóa sinh trắc nhưng chưa quét
    (0.80, None, False, False),                                    # không có sinh trắc -> cần ≥ 85%
    (0.90, None, False, True),
])
def test_dual_authentication_rule(knowledge, bio, has_lock, expected, settings):
    from evolving_soul import legacy
    ok, reason = legacy.decide(knowledge, bio, has_lock, settings)
    assert ok is expected
    assert bool(reason) is not expected
