"""
Kiểm thử trích xuất đặc trưng & chấm điểm 5 trụ cột (V3).
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from evolving_soul import features, scoring
from evolving_soul.config import Settings
from evolving_soul.crypto import SoulCipher, new_master_key
from tests import synthetic

DEVICE = ("PC-HUNG|Windows|AMD64", "Windows")
OWNER = {
    "google": "hahuuhung1985@gmail.com",
    "dob": "1985-05-15",
    "family": "Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi",
    "traits": ["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
    "password": "HungAI@1985#Secret",
    "answer": "Tôi luôn tìm thấy sự bình yên khi viết code AI vào ban đêm và uống trà nóng.",
}


@pytest.fixture
def cipher() -> SoulCipher:
    return SoulCipher(new_master_key())


def test_parse_family_names_strips_relations_and_diacritics():
    names = features.parse_family_names("Bố Hà Văn A; Con trai Hà Minh Khôi,  vợ TRẦN THỊ C\nHa Minh Khoi, Mẹ")
    assert names == ["ha van a", "ha minh khoi", "tran thi c"]
    # Họ Hồ / Dương không bị coi là từ quan hệ
    assert features.parse_family_names("Hồ Văn Minh, Anh Dương Thị Lan") == ["ho van minh", "duong thi lan"]


def test_password_pattern_and_features_hold_no_plaintext():
    assert features.password_pattern("HungAI@1985#Secret") == "ULUSDSUL"
    length, diversity = features.password_features("HungAI@1985#Secret")
    assert length == pytest.approx(18 / 20)
    assert diversity == 1.0
    assert features.password_features("") == (0.0, 0.0)


def test_style_features_bounded():
    for text in ["", "a", "Một câu. Hai câu! Ba câu?", "x" * 500]:
        values = features.style_features(text)
        assert len(values) == 3
        assert all(0.0 <= v <= 1.0 for v in values)


def test_observation_contains_only_digests(cipher):
    obs = features.observe(OWNER, cipher, DEVICE)
    blob = repr(obs)
    for secret in ["1985-05-15", "Khôi", "khoi", "HungAI", "Secret", "hahuuhung1985", "bình yên"]:
        assert secret not in blob
    assert len(obs.family) == 4
    assert obs.dob and len(obs.dob) == 64


def test_vector_has_14_dimensions(cipher):
    obs = features.observe(OWNER, cipher, DEVICE)
    model = scoring.build_model(obs)
    assert len(model["vector"]) == features.VECTOR_DIM == 14
    result = scoring.compare(obs, model, Settings())
    assert result["vector"].shape == (14,)


def test_owner_matches_self_perfectly(cipher):
    obs = features.observe(OWNER, cipher, DEVICE)
    model = scoring.build_model(obs)
    result = scoring.compare(obs, model, Settings())
    assert result["is_owner"]
    assert result["trust_score"] == pytest.approx(1.0)
    assert all(v == pytest.approx(1.0) for v in result["pillars"].values())


def test_aging_owner_passes_and_stranger_fails(cipher):
    model = scoring.build_model(features.observe(OWNER, cipher, DEVICE))
    aging = dict(OWNER, family="Vợ Trần Thị C, Con trai Ha Minh Khoi", password="HungAI@2031#NewPass",
                 answer="Sự bình yên nhất với tôi là viết code AI ban đêm và uống trà cùng gia đình.")
    assert scoring.compare(features.observe(aging, cipher, DEVICE), model, Settings())["is_owner"]

    stranger = {"dob": "1995-01-01", "family": "Không rõ", "traits": ["Ưa mạo hiểm"], "password": "123456password",
                "answer": "Tôi thích đi du lịch biển và chơi game thâu đêm."}
    result = scoring.compare(features.observe(stranger, cipher, DEVICE), model, Settings())
    assert not result["gate_passed"]
    assert not result["is_owner"]
    assert result["trust_score"] < 0.4


def test_hard_gate_blocks_high_behavioral_score_without_knowledge(cipher):
    model = scoring.build_model(features.observe(OWNER, cipher, DEVICE))
    mimic = dict(OWNER, dob="2000-01-01", family="Nguyễn Văn X")  # copy văn phong + mật khẩu, không biết gia đình
    result = scoring.compare(features.observe(mimic, cipher, DEVICE), model, Settings())
    assert not result["gate_passed"]
    assert not result["is_owner"]


def test_oauth_pillar_absent_when_owner_never_linked(cipher):
    data = dict(OWNER, google="")
    model = scoring.build_model(features.observe(data, cipher, DEVICE))
    result = scoring.compare(features.observe(data, cipher, DEVICE), model, Settings())
    assert result["pillars"]["oauth"] is None
    assert scoring.baseline_radar(model)["Định danh OAuth (SSO)"] == 0.0


def test_ema_evolution_moves_behavior_dims_by_alpha(cipher):
    settings = Settings()
    obs0 = features.observe(OWNER, cipher, DEVICE)
    model = scoring.build_model(obs0)
    newer = dict(OWNER, password="HungAI@1985#SecretLonger!!")
    obs1 = features.observe(newer, cipher, ("LAPTOP|Darwin|arm64", "Darwin"))
    result = scoring.compare(obs1, model, settings)
    evolved = scoring.evolve(model, obs1, result["vector"], settings)

    old, new, x = np.array(model["vector"]), np.array(evolved["vector"]), result["vector"]
    i = features.IDX_PW_LEN
    assert new[i] == pytest.approx(0.85 * old[i] + 0.15 * x[i], abs=1e-6)
    assert new[features.IDX_DOB] == 1.0  # chiều khớp chính xác không bị EMA
    assert len(evolved["devices"]) == 2  # học thêm thiết bị mới
    assert model["oauth"] == evolved["oauth"]  # không đột biến mô hình gốc


def test_keyword_memory_is_bounded_by_frequency(cipher):
    settings = Settings(max_keywords=5)
    model = scoring.build_model(features.observe(OWNER, cipher, DEVICE))
    for i in range(10):
        obs = features.observe(dict(OWNER, answer=f"code trà code tu{i} hoc{i}"), cipher, DEVICE)
        model = scoring.evolve(model, obs, scoring.compare(obs, model, settings)["vector"], settings)
    assert len(model["keywords"]) == 5
    assert cipher.digest("code", "keyword") in model["keywords"]


def test_calibration_far_frr_on_synthetic_population(cipher):
    """Hiệu chỉnh trên tập giả lập độc lập với tập dùng để chọn trọng số (seed khác)."""
    settings = Settings()
    rng = random.Random(2026)
    outcomes = {"owner": [], "stranger": [], "insider": []}
    for _ in range(150):
        person = synthetic.owner_base(rng)
        model = scoring.build_model(features.observe(person["registration"], cipher, person["device"]))
        for kind, make, n in (("owner", synthetic.owner_session, 3), ("stranger", synthetic.stranger, 3),
                              ("insider", synthetic.insider, 2)):
            for _ in range(n):
                data, device = make(person, rng)
                outcomes[kind].append(scoring.compare(features.observe(data, cipher, device), model, settings)["is_owner"])

    frr = 1 - np.mean(outcomes["owner"])
    far_stranger = np.mean(outcomes["stranger"])
    far_insider = np.mean(outcomes["insider"])
    assert frr <= 0.07, f"FRR={frr:.3f}"
    assert far_stranger <= 0.01, f"FAR người lạ={far_stranger:.3f}"
    assert far_insider <= 0.06, f"FAR người nhà={far_insider:.3f}"
