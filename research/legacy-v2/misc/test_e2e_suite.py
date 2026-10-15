"""
Bộ Kiểm Thử Đầu-Cuối (End-to-End E2E Test Suite)
Dự án: Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bao gồm 6 kịch bản kiểm thử bảo mật, tiến hóa thời gian và chuyển giao di sản 2 năm.
"""

import os
import shutil
import cv2
import numpy as np
import pytest
from core_engine import EvolvingOwnerAI_V2


def generate_synthetic_face_bytes(seed_val: int = 42) -> bytes:
    """Tạo ảnh sinh trắc học giả lập (mô phỏng Camera/Upload) có cấu trúc khuôn mặt đặc trưng theo seed."""
    np.random.seed(seed_val)
    img = np.zeros((200, 200), dtype=np.uint8)
    # Vẽ cấu trúc khuôn mặt với độ tương phản theo seed
    cv2.circle(img, (100, 100), 70, int(150 + (seed_val % 80)), -1)
    cv2.circle(img, (75, 80), 12, 30, -1)
    cv2.circle(img, (125, 80), 12, 30, -1)
    cv2.ellipse(img, (100, 130), (30, 15), 0, 0, 180, 40, 4)
    _, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes()


@pytest.fixture(scope="module")
def ai_e2e():
    """Tạo môi trường két sắt độc lập để kiểm thử, tự dọn dẹp sau khi chạy."""
    test_vault_dir = "vault_e2e_test"
    ai = EvolvingOwnerAI_V2(secret_key_phrase="e2e_production_test_key_1985", vault_dir=test_vault_dir, demo_mode=True)

    if os.path.exists(test_vault_dir):
        shutil.rmtree(test_vault_dir)
    os.makedirs(test_vault_dir, exist_ok=True)

    yield ai

    # Dọn dẹp két sắt test
    if os.path.exists(test_vault_dir):
        shutil.rmtree(test_vault_dir)


# =====================================================================
# KỊCH BẢN 1: KHỞI TẠO HỒ SƠ CHỦ NHÂN & KIỂM TRA MÃ HÓA ZERO-KNOWLEDGE
# =====================================================================
def test_step1_owner_onboarding_and_encryption(ai_e2e):
    owner_data = {
        "owner_name": "HÀ HỮU HƯNG (1985)",
        "google": "hahuuhung1985@gmail.com",
        "apple": "hung8x@icloud.com",
        "facebook": "fb.com/hahuuhung85",
        "dob": "1985-05-15",
        "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
        "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
        "password": "HungAI@1985#Secret",
        "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng."
    }
    profile = ai_e2e.register_owner(owner_data)

    assert os.path.exists(ai_e2e.vault_path), "Lỗi: Không tạo được file két sắt mã hóa!"
    assert profile["generation"] == 1
    assert len(profile["evolving_vector"]) == 14, "Lỗi: Vector đặc trưng không đủ 14 chiều!"

    # Kiểm tra an toàn Zero-Knowledge: plaintext tuyệt đối không được ghi ra đĩa
    with open(ai_e2e.vault_path, "rb") as f:
        raw_encrypted_disk = f.read()
    assert b"HungAI@1985#Secret" not in raw_encrypted_disk, "CẢNH BÁO BẢO MẬT: Mật khẩu bị lộ dưới dạng plaintext!"
    assert b"Minh Khoi" not in raw_encrypted_disk, "CẢNH BÁO BẢO MẬT: Tên gia đình không được mã hóa an toàn!"


# =====================================================================
# KỊCH BẢN 2: CHỦ NHÂN GIÀ ĐI, ĐỔI MẬT KHẨU & TỰ ĐỘNG TIẾN HÓA (GEN #2)
# =====================================================================
def test_step2_owner_aging_and_continual_evolution(ai_e2e):
    # Giả lập 5 năm sau: Đổi mật khẩu nhưng giữ quy luật, thay đổi nhẹ cá tính
    aging_owner_data = {
        "google": "hahuuhung1985@gmail.com",
        "apple": "hung8x@icloud.com",
        "facebook": "fb.com/hahuuhung85",
        "dob": "1985-05-15",
        "family": "Vợ Trần Thị C, Con trai Hà Minh Khôi, Bố Hà Văn A",
        "traits": ["Thích công nghệ", "Logic & Lý trí", "Dậy sớm"],
        "password": "HungAI@2031#NewPass",
        "answer": "Sự bình yên nhất với tôi là ngồi viết code AI và uống trà cùng gia đình."
    }
    res = ai_e2e.verify_and_evolve(aging_owner_data)

    assert res is not None, "Lỗi: Hàm verify_and_evolve trả về None!"
    assert res["is_owner"] is True, f"Lỗi: Không nhận ra Chủ nhân khi đổi nhẹ thói quen! Điểm: {res['trust_score']}"
    assert res["generation"] == 2, "Lỗi: Hồ sơ không tự tiến hóa lên Gen #2!"
    assert res["trust_score"] >= 0.72


# =====================================================================
# KỊCH BẢN 3: CHẶN ĐỨNG KẺ MẠO DANH / NGƯỜI LẠ (IMPOSTER REJECTION)
# =====================================================================
def test_step3_imposter_attack_blocked(ai_e2e):
    hacker_data = {
        "google": "hacker_anonymous@gmail.com",
        "apple": "",
        "facebook": "",
        "dob": "1995-01-01",
        "family": "Không rõ tên người thân nào",
        "traits": ["Ưa mạo hiểm", "Hướng ngoại"],
        "password": "123456password",
        "answer": "Tôi thích đi du lịch biển và chơi game thâu đêm."
    }
    res = ai_e2e.verify_and_evolve(hacker_data)

    assert res is not None
    assert res["is_owner"] is False, "CẢNH BÁO NGUY HIỂM: Hệ thống nhận nhầm người lạ là Chủ nhân!"
    assert res["trust_score"] < 0.50
    assert res["generation"] == 2, "Lỗi: Kẻ lạ mặt làm sai lệch thế hệ tiến hóa của Chủ nhân!"


# =====================================================================
# KỊCH BẢN 4: NIÊM PHONG BẢN QUYỀN SÁNG TẠO & SINH TRẮC HỌC NGƯỜI THỪA KẾ
# =====================================================================
def test_step4_setup_digital_legacy_with_biometrics(ai_e2e):
    heir_face_bytes = generate_synthetic_face_bytes(seed_val=100)
    assets = [
        "Bản quyền Mã nguồn Mở Evolving Soul AI - Tác giả: HÀ HỮU HƯNG (1985) - Kỹ sư AI thế hệ 8X",
        "Kho lưu trữ Sáng tác & Bản thảo cá nhân: https://github.com/hahuuhung1985/evolving-soul-ai",
        "Khóa giải mã Kho tài sản số trí tuệ: MASTER-KEY-8X-2026"
    ]
    leg_cfg = ai_e2e.setup_digital_legacy(
        heir_name="Hà Minh Khôi",
        heir_email="khoi.ha@gmail.com",
        family_secret="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        assets_list=assets,
        message_to_kin="Con hãy tiếp tục phát triển dự án AI này và giữ vững đạo đức nghề nghiệp.",
        heir_bio_bytes=heir_face_bytes,
        inactivity_days=730,
        owner_session_verified=True
    )
    assert leg_cfg["inactivity_threshold_days"] == 730
    assert leg_cfg["heir_biometric_vector"] is not None, "Lỗi: Không trích xuất được Vector sinh trắc học người thừa kế!"


# =====================================================================
# KỊCH BẢN 5: NGƯỜI THÂN TRUY CẬP KHI CHỦ NHÂN CÒN ONLINE (< 2 NĂM)
# =====================================================================
def test_step5_kin_access_before_2_years_locked(ai_e2e):
    heir_face_bytes = generate_synthetic_face_bytes(seed_val=100)
    # Giả lập Chủ nhân mới offline 100 ngày (Chưa chạm mốc 730 ngày)
    res = ai_e2e.verify_kin_with_biometrics(
        kin_name="Hà Minh Khôi",
        kin_email="khoi.ha@gmail.com",
        owner_dob="1985-05-15",
        other_family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        family_secret_input="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        live_bio_bytes=heir_face_bytes,
        simulated_days_offline=100
    )
    assert res["is_verified"] is True, "Lỗi: Không nhận diện được người thân hợp lệ!"
    assert res["is_unlockable"] is False, "Lỗi: Chưa đủ 2 năm (730 ngày) nhưng hệ thống đã báo mở khóa!"
    assert res["is_unlocked"] is False
    assert len(res["assets"]) == 0, "CẢNH BÁO BẢO MẬT: Lộ tài sản khi Chủ nhân vẫn còn trong chu kỳ online!"


# =====================================================================
# KỊCH BẢN 6: SAU 2 NĂM (730 NGÀY) OFFLINE -> QUÉT SINH TRẮC MỞ KHÓA DI SẢN
# =====================================================================
def test_step6_kin_biometric_unlock_after_2_years(ai_e2e):
    heir_face_bytes = generate_synthetic_face_bytes(seed_val=100)
    # Giả lập Chủ nhân đã offline 735 ngày (> 730 ngày)
    res = ai_e2e.verify_kin_with_biometrics(
        kin_name="Hà Minh Khôi",
        kin_email="khoi.ha@gmail.com",
        owner_dob="1985-05-15",
        other_family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
        family_secret_input="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
        live_bio_bytes=heir_face_bytes,
        simulated_days_offline=735
    )
    assert res["is_unlockable"] is True
    assert res["is_verified"] is True
    assert res["is_unlocked"] is True
    assert res["bio_score"] >= 0.95, "Lỗi: Điểm khớp sinh trắc học người thừa kế không đạt chuẩn!"
    assert len(res["assets"]) == 3, "Lỗi: Không bàn giao đầy đủ 3 tài sản số cho người thừa kế!"
    assert "HÀ HỮU HƯNG (1985)" in res["assets"][0]
