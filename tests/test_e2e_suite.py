"""
Bộ Kiểm Thử Đầu-Cuối (E2E) V3 — Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X

Kịch bản 1–6: hành trình gốc của V2 (khởi tạo, già đi & tiến hóa, chặn mạo danh, niêm phong di sản,
người thân trước/sau 730 ngày), chạy theo thứ tự trên cùng một két sắt.
Kịch bản 7–12: các lỗ hổng đã vá ở V3 (ghi đè hồ sơ, niêm phong khi chưa xác minh, giả lập thời gian
ngoài demo, sai passphrase, sửa nhật ký, chống dò).
"""

from __future__ import annotations

import json

import pytest

from evolving_soul import EvolvingSoulEngine, LockedOutError, OwnerNotVerifiedError, ProfileExistsError, VaultLockedError
from evolving_soul.biometrics import FaceBiometrics
from evolving_soul.config import Settings
from tests.conftest import FAST_KDF_N, PASSPHRASE
from tests.test_biometrics import synthetic_face_bytes
from tests.test_engine_owner import FakeClock

DEVICE = ("PC-HUNG|Windows|AMD64", "Windows")
OWNER = {
    "owner_name": "HÀ HỮU HƯNG (1985)",
    "google": "hahuuhung1985@gmail.com",
    "apple": "hung8x@icloud.com",
    "facebook": "fb.com/hahuuhung85",
    "dob": "1985-05-15",
    "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
    "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
    "password": "HungAI@1985#Secret",
    "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng.",
}
AGING_OWNER = {  # 5 năm sau: đổi mật khẩu theo thói quen, cá tính đổi nhẹ, nêu một phần người thân
    "google": "hahuuhung1985@gmail.com",
    "dob": "1985-05-15",
    "family": "Vợ Trần Thị C, Con trai Ha Minh Khoi, Bố Hà Văn A",
    "traits": ["Thích công nghệ", "Logic & Lý trí", "Dậy sớm"],
    "password": "HungAI@2031#NewPass",
    "answer": "Sự bình yên nhất với tôi là ngồi viết code AI và uống trà cùng gia đình.",
}
HACKER = {
    "google": "hacker_anonymous@gmail.com",
    "dob": "1995-01-01",
    "family": "Không rõ tên người thân nào",
    "traits": ["Ưa mạo hiểm", "Hướng ngoại"],
    "password": "123456password",
    "answer": "Tôi thích đi du lịch biển và chơi game thâu đêm.",
}
SECRET = "Kỷ niệm ngôi nhà phố cổ Hà Nội 1985"
ASSETS = [
    "Bản quyền Mã nguồn Mở Evolving Soul AI - Tác giả: HÀ HỮU HƯNG (1985) - Kỹ sư AI thế hệ 8X",
    "Kho lưu trữ Sáng tác & Bản thảo cá nhân",
    "Khóa giải mã Kho tài sản số trí tuệ: MASTER-KEY-8X-2026",
]
KIN = dict(kin_name="Hà Minh Khôi", kin_email="khoi.ha@gmail.com", owner_dob="1985-05-15",
           family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C", family_secret=SECRET)


def make_engine(settings: Settings, clock: FakeClock) -> EvolvingSoulEngine:
    return EvolvingSoulEngine(settings, clock=clock, device_probe=lambda: DEVICE,
                              biometrics=FaceBiometrics(settings.model_dir, allow_download=False))


@pytest.fixture(scope="module")
def journey(tmp_path_factory):
    """Một két sắt dùng chung cho kịch bản 1–6 (chạy theo thứ tự như bộ E2E V2)."""
    root = tmp_path_factory.mktemp("e2e")
    settings = Settings(vault_dir=root / "vault", model_dir=root / "models", kdf_n=FAST_KDF_N, demo_mode=True)
    clock = FakeClock()
    owner = make_engine(settings, clock)
    owner.create_vault(PASSPHRASE)
    return {"settings": settings, "clock": clock, "owner": owner}


# =====================================================================
# KỊCH BẢN 1: KHỞI TẠO HỒ SƠ & KIỂM TRA ZERO-KNOWLEDGE
# =====================================================================
def test_step1_owner_onboarding_and_encryption(journey):
    owner = journey["owner"]
    profile = owner.register_owner(OWNER)
    assert profile["generation"] == 1
    assert len(profile["model"]["vector"]) == 14, "Vector đặc trưng phải đủ 14 chiều (5 trụ cột)"
    for path in journey["settings"].vault_dir.iterdir():
        raw = path.read_bytes()
        for secret in ["HungAI@1985#Secret", "Khôi", "1985-05-15", "hahuuhung1985", PASSPHRASE]:
            assert secret.encode("utf-8") not in raw, f"Lộ '{secret}' trong {path.name}"


# =====================================================================
# KỊCH BẢN 2: CHỦ NHÂN GIÀ ĐI, ĐỔI MẬT KHẨU & TỰ TIẾN HÓA (GEN #2)
# =====================================================================
def test_step2_owner_aging_and_continual_evolution(journey):
    res = journey["owner"].verify_owner(AGING_OWNER)
    assert res["is_owner"], f"Không nhận ra Chủ nhân khi đổi nhẹ thói quen! Điểm: {res['trust_score']:.3f}"
    assert res["generation"] == 2
    assert res["trust_score"] >= res["threshold"]


# =====================================================================
# KỊCH BẢN 3: CHẶN KẺ MẠO DANH
# =====================================================================
def test_step3_imposter_attack_blocked(journey):
    res = journey["owner"].verify_owner(HACKER)
    assert not res["is_owner"] and not res["gate_passed"]
    assert res["trust_score"] < 0.5
    assert res["generation"] == 2, "Kẻ lạ mặt không được làm thay đổi thế hệ tiến hóa"


# =====================================================================
# KỊCH BẢN 4: NIÊM PHONG DI SẢN & SINH TRẮC NGƯỜI THỪA KẾ
# =====================================================================
def test_step4_setup_digital_legacy_with_biometrics(journey):
    owner = journey["owner"]
    owner.verify_owner(AGING_OWNER)  # phiên Chủ nhân hợp lệ
    status = owner.seal_legacy(heir_name="Hà Minh Khôi", heir_email="khoi.ha@gmail.com", family_secret=SECRET,
                               assets=ASSETS, message="Con hãy tiếp tục phát triển dự án AI này.",
                               heir_images=[synthetic_face_bytes(100)])
    assert status["threshold_days"] == 730
    assert status["has_biometric_lock"] and status["asset_count"] == 3


# =====================================================================
# KỊCH BẢN 5: NGƯỜI THÂN TRUY CẬP KHI CHỦ NHÂN CÒN HOẠT ĐỘNG (< 730 NGÀY)
# =====================================================================
def test_step5_kin_access_before_2_years_locked(journey):
    portal = make_engine(journey["settings"], journey["clock"])
    portal.set_demo_offset_days(100)
    res = portal.claim_legacy(**KIN, live_image=synthetic_face_bytes(100))
    assert res["is_verified"], "Người thân hợp lệ phải được nhận diện"
    assert not res["is_unlockable"] and not res["is_unlocked"]
    assert res["assets"] == [], "Không được lộ tài sản khi Chủ nhân còn trong chu kỳ hoạt động"


# =====================================================================
# KỊCH BẢN 6: SAU 730 NGÀY -> QUÉT SINH TRẮC MỞ KHÓA DI SẢN
# =====================================================================
def test_step6_kin_biometric_unlock_after_2_years(journey):
    portal = make_engine(journey["settings"], journey["clock"])
    portal.set_demo_offset_days(735)
    res = portal.claim_legacy(**KIN, live_image=synthetic_face_bytes(100))
    assert res["is_unlockable"] and res["is_verified"] and res["is_unlocked"]
    assert res["bio"]["passed"]
    assert res["assets"] == ASSETS
    assert "HÀ HỮU HƯNG (1985)" in res["assets"][0]


# =====================================================================
# KỊCH BẢN 7–12: CÁC LỖ HỔNG V2 ĐÃ ĐƯỢC VÁ
# =====================================================================
@pytest.fixture
def fresh(settings):
    demo = settings.with_overrides(demo_mode=True)
    eng = make_engine(demo, FakeClock())
    eng.create_vault(PASSPHRASE)
    eng.register_owner(OWNER)
    return eng


def test_step7_profile_cannot_be_overwritten_by_stranger(fresh):
    with pytest.raises(ProfileExistsError):
        fresh.register_owner(dict(HACKER, owner_name="HACKER"))
    with pytest.raises(OwnerNotVerifiedError):
        fresh.register_owner(dict(HACKER, owner_name="HACKER"), force=True)
    assert fresh.profile["owner_name"] == "HÀ HỮU HƯNG (1985)"


def test_step8_legacy_cannot_be_sealed_without_owner_verification(fresh):
    fresh.verify_owner(HACKER)
    with pytest.raises(OwnerNotVerifiedError):
        fresh.seal_legacy(heir_name="Kẻ gian", heir_email="x@y.z", family_secret="mat uoc ke gian", assets=["X"], message="")


def test_step9_time_simulation_only_in_demo(settings):
    eng = make_engine(settings, FakeClock())  # settings mặc định: không phải demo
    with pytest.raises(PermissionError):
        eng.set_demo_offset_days(1000)


def test_step10_wrong_passphrase_cannot_open_vault(fresh, settings):
    other = make_engine(settings, FakeClock())
    with pytest.raises(VaultLockedError):
        other.unlock("doan-mo-passphrase")
    assert other.profile is None


def test_step11_audit_log_tampering_detected(fresh, settings):
    fresh.verify_owner(OWNER)
    log = settings.vault_dir / "audit.jsonl"
    lines = log.read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[-1])
    entry["result"] = "gia_mao"
    lines[-1] = json.dumps(entry, ensure_ascii=False)
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not fresh.audit_integrity()["ok"]


def test_step12_brute_force_locked_out(fresh, settings):
    for _ in range(settings.max_failed_attempts):
        fresh.verify_owner(HACKER)
    with pytest.raises(LockedOutError):
        fresh.verify_owner(OWNER)
