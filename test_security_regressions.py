"""
Kiểm thử hồi quy bảo mật (Giai đoạn 0)
Dự án: Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import pytest
from core_engine import EvolvingOwnerAI_V2

OWNER_DATA = {
    "owner_name": "HÀ HỮU HƯNG (1985)",
    "dob": "1985-05-15",
    "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
    "traits": ["Thích công nghệ", "Logic & Lý trí"],
    "password": "HungAI@1985#Secret",
    "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm.",
}

LEGACY_ARGS = dict(
    heir_name="Hà Minh Khôi",
    heir_email="khoi.ha@gmail.com",
    family_secret="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
    assets_list=["MASTER-KEY-8X-2026"],
    message_to_kin="Giữ vững đạo đức nghề nghiệp.",
)

KIN_ARGS = dict(
    kin_name="Hà Minh Khôi",
    kin_email="khoi.ha@gmail.com",
    owner_dob="1985-05-15",
    other_family_members="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C",
    family_secret_input="Kỷ niệm ngôi nhà phố cổ Hà Nội 1985",
)


def make_ai(tmp_path, demo_mode: bool = False) -> EvolvingOwnerAI_V2:
    return EvolvingOwnerAI_V2(secret_key_phrase="regression_key", vault_dir=str(tmp_path / "vault"), demo_mode=demo_mode)


def test_register_cannot_overwrite_existing_owner(tmp_path):
    ai = make_ai(tmp_path)
    ai.register_owner(OWNER_DATA)
    hacker = dict(OWNER_DATA, owner_name="HACKER", dob="1999-01-01")

    with pytest.raises(PermissionError):
        ai.register_owner(hacker)
    with pytest.raises(PermissionError):
        ai.register_owner(hacker, force=True)  # force mà chưa xác minh vẫn bị chặn
    assert ai.load_profile()["owner_name"] == "HÀ HỮU HƯNG (1985)"

    ai.register_owner(dict(OWNER_DATA, owner_name="Chủ nhân mới"), force=True, owner_verified=True)
    assert ai.load_profile()["owner_name"] == "Chủ nhân mới"


def test_legacy_seal_requires_owner_verification(tmp_path):
    ai = make_ai(tmp_path)
    ai.register_owner(OWNER_DATA)

    with pytest.raises(PermissionError):
        ai.setup_digital_legacy(**LEGACY_ARGS)
    assert "legacy_config" not in ai.load_profile()


def test_simulated_days_ignored_outside_demo_mode(tmp_path):
    ai = make_ai(tmp_path, demo_mode=False)
    ai.register_owner(OWNER_DATA)
    ai.setup_digital_legacy(**LEGACY_ARGS, owner_session_verified=True)

    status = ai.check_inactivity_status(simulated_days_offline=1000)
    assert status["is_unlockable"] is False
    assert status["elapsed_days"] < 1

    res = ai.verify_kin_with_biometrics(**KIN_ARGS, simulated_days_offline=1000)
    assert res["is_unlocked"] is False
    assert res["assets"] == []
    assert ai.load_profile()["legacy_config"]["inheritance_claimed"] is False


def test_simulated_days_allowed_in_demo_mode(tmp_path):
    ai = make_ai(tmp_path, demo_mode=True)
    ai.register_owner(OWNER_DATA)
    ai.setup_digital_legacy(**LEGACY_ARGS, owner_session_verified=True)

    assert ai.check_inactivity_status(simulated_days_offline=1000)["is_unlockable"] is True


def test_demo_mode_reads_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("EVOLVING_SOUL_DEMO", "1")
    assert EvolvingOwnerAI_V2(vault_dir=str(tmp_path / "a")).demo_mode is True
    monkeypatch.delenv("EVOLVING_SOUL_DEMO")
    assert EvolvingOwnerAI_V2(vault_dir=str(tmp_path / "b")).demo_mode is False
