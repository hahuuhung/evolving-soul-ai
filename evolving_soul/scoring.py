"""
Chấm điểm 5 trụ cột, Điểm Tin Cậy (Trust Score) và tiến hóa EMA (V3).

Điểm từng trụ cột ∈ [0, 1]:
  oauth    : trung bình khớp trên các tài khoản Chủ nhân đã liên kết (None nếu Chủ nhân chưa liên kết tài khoản nào)
  family   : 0.4 * khớp ngày sinh + 0.6 * độ phủ tên người thân
  style    : 0.4 * độ gần văn phong + 0.4 * tỷ lệ từ khóa quen thuộc + 0.2 * Jaccard cá tính
  password : 0.1 * độ gần độ dài + 0.1 * độ gần độ đa dạng + 0.8 * khớp thói quen (tiền tố & cấu trúc)
  device   : 0.7 * thiết bị tin cậy + 0.3 * cùng hệ điều hành

Trust Score = trung bình có trọng số (Settings.pillar_weights) trên các trụ cột có mặt.
Cổng cứng: phải khớp ngày sinh HOẶC ≥ 50% người thân, nếu không thì luôn bị từ chối.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from evolving_soul.config import Settings
from evolving_soul.crypto import digests_equal
from evolving_soul.features import (
    EVOLVING_DIMS,
    IDX_DEVICE,
    IDX_DOB,
    IDX_FAMILY,
    IDX_OS,
    IDX_PW_DIV,
    IDX_PW_HABIT,
    IDX_PW_LEN,
    IDX_STYLE,
    OAUTH_PROVIDERS,
    VECTOR_DIM,
    Observation,
)

PILLARS = ("oauth", "family", "style", "password", "device")
PILLAR_LABELS = {
    "oauth": "Định danh OAuth (SSO)",
    "family": "Ký ức Gia đình & Ngày sinh",
    "style": "Cá tính & Văn phong Ngôn ngữ",
    "password": "Thói quen Cấu trúc Mật khẩu",
    "device": "Dấu vân tay Thiết bị",
}

STYLE_TOLERANCE = 0.25
PW_LEN_TOLERANCE = 0.30
FAMILY_FULL_COVERAGE = 3  # nêu đúng 3 người thân (hoặc tất cả nếu ít hơn) = độ phủ 100%


def _closeness(a: float, b: float, tolerance: float) -> float:
    return float(max(0.0, 1.0 - abs(a - b) / tolerance))


def _contains(digests: list[str], value: str | None) -> bool:
    return any(digests_equal(d, value) for d in digests)


# =========================================================================
# MÔ HÌNH CHỦ NHÂN
# =========================================================================

def build_model(obs: Observation) -> dict:
    """Mô hình tham chiếu ban đầu (Gen #1) từ phiên đăng ký."""
    linked = [p for p in OAUTH_PROVIDERS if obs.oauth.get(p)]
    vector = np.zeros(VECTOR_DIM, dtype=float)
    for i, p in enumerate(OAUTH_PROVIDERS):
        vector[i] = 1.0 if p in linked else 0.0
    vector[3] = 1.0 if linked else 0.0
    vector[IDX_DOB] = vector[IDX_FAMILY] = vector[IDX_PW_HABIT] = vector[IDX_DEVICE] = vector[IDX_OS] = 1.0
    vector[IDX_STYLE] = obs.style
    vector[IDX_PW_LEN] = obs.pw_len
    vector[IDX_PW_DIV] = obs.pw_diversity
    return {
        "oauth": dict(obs.oauth),
        "dob": obs.dob,
        "family": sorted(obs.family),
        "traits": sorted(obs.traits),
        "keywords": dict(obs.keywords),
        "pw_prefixes": [obs.pw_prefix] if obs.pw_prefix else [],
        "pw_patterns": [obs.pw_pattern] if obs.pw_pattern else [],
        "devices": [obs.device] if obs.device else [],
        "os_families": [obs.os_family] if obs.os_family else [],
        "vector": vector.round(6).tolist(),
    }


def baseline_radar(model: dict) -> dict[str, float]:
    """Radar gốc: 1.0 cho mọi trụ cột, trừ OAuth khi Chủ nhân chưa liên kết tài khoản."""
    radar = {PILLAR_LABELS[p]: 1.0 for p in PILLARS}
    if not any(model["oauth"].values()):
        radar[PILLAR_LABELS["oauth"]] = 0.0
    return radar


# =========================================================================
# SO KHỚP
# =========================================================================

def compare(obs: Observation, model: dict, settings: Settings) -> dict:
    """So khớp một phiên với mô hình Chủ nhân -> vector X, điểm trụ cột, Trust Score, cổng cứng."""
    ref = np.asarray(model["vector"], dtype=float)
    x = np.zeros(VECTOR_DIM, dtype=float)

    # Trụ cột 1 — OAuth
    linked = [p for p in OAUTH_PROVIDERS if model["oauth"].get(p)]
    for i, p in enumerate(OAUTH_PROVIDERS):
        x[i] = 1.0 if digests_equal(model["oauth"].get(p), obs.oauth.get(p)) else 0.0
    x[3] = float(sum(x[i] for i, p in enumerate(OAUTH_PROVIDERS) if p in linked) / len(linked)) if linked else 0.0
    oauth_score = float(x[3]) if linked else None

    # Trụ cột 2 — Ký ức gia đình
    saved_family = list(model["family"])
    matched = sum(1 for d in obs.family if _contains(saved_family, d))
    needed = max(1, min(FAMILY_FULL_COVERAGE, len(saved_family)))
    x[IDX_DOB] = 1.0 if digests_equal(model["dob"], obs.dob) else 0.0
    x[IDX_FAMILY] = min(1.0, matched / needed)
    family_score = 0.4 * x[IDX_DOB] + 0.6 * x[IDX_FAMILY]

    # Trụ cột 3 — Văn phong & cá tính
    x[IDX_STYLE] = obs.style
    style_close = float(np.mean([_closeness(a, b, STYLE_TOLERANCE) for a, b in zip(ref[IDX_STYLE], x[IDX_STYLE])]))
    words = list(obs.keywords)
    keyword_overlap = (sum(1 for w in words if w in model["keywords"]) / len(words)) if words else 0.0
    saved_traits = set(model["traits"])
    union = saved_traits | obs.traits
    traits_jaccard = len(saved_traits & obs.traits) / len(union) if union else 0.0
    style_score = 0.4 * style_close + 0.4 * keyword_overlap + 0.2 * traits_jaccard

    # Trụ cột 4 — Thói quen mật khẩu
    x[IDX_PW_LEN] = obs.pw_len
    x[IDX_PW_DIV] = obs.pw_diversity
    prefix_hit = _contains(model["pw_prefixes"], obs.pw_prefix)
    pattern_hit = _contains(model["pw_patterns"], obs.pw_pattern)
    x[IDX_PW_HABIT] = 0.5 * prefix_hit + 0.5 * pattern_hit
    password_score = (
        0.1 * _closeness(ref[IDX_PW_LEN], x[IDX_PW_LEN], PW_LEN_TOLERANCE)
        + 0.1 * (1.0 - abs(ref[IDX_PW_DIV] - x[IDX_PW_DIV]))
        + 0.8 * x[IDX_PW_HABIT]
    )

    # Trụ cột 5 — Thiết bị
    x[IDX_DEVICE] = 1.0 if _contains(model["devices"], obs.device) else 0.0
    x[IDX_OS] = 1.0 if _contains(model["os_families"], obs.os_family) else 0.0
    device_score = 0.7 * x[IDX_DEVICE] + 0.3 * x[IDX_OS]

    pillars = {
        "oauth": oauth_score,
        "family": float(family_score),
        "style": float(style_score),
        "password": float(password_score),
        "device": float(device_score),
    }
    trust = weighted_trust(pillars, settings.pillar_weights)
    gate = bool(x[IDX_DOB] == 1.0 or x[IDX_FAMILY] >= 0.5)
    return {
        "vector": x,
        "pillars": pillars,
        "trust_score": trust,
        "gate_passed": gate,
        "is_owner": gate and trust >= settings.owner_threshold,
        "details": {
            "dob_match": bool(x[IDX_DOB]),
            "family_coverage": float(x[IDX_FAMILY]),
            "style_closeness": style_close,
            "keyword_overlap": keyword_overlap,
            "traits_jaccard": traits_jaccard,
            "pw_prefix_match": prefix_hit,
            "pw_pattern_match": pattern_hit,
            "trusted_device": bool(x[IDX_DEVICE]),
        },
    }


def weighted_trust(pillars: dict[str, float | None], weights: dict[str, float]) -> float:
    present = {p: s for p, s in pillars.items() if s is not None}
    total = sum(weights[p] for p in present)
    return float(sum(weights[p] * s for p, s in present.items()) / total) if total else 0.0


def radar_from_pillars(pillars: dict[str, float | None]) -> dict[str, float]:
    return {PILLAR_LABELS[p]: float(pillars[p] or 0.0) for p in PILLARS}


# =========================================================================
# TIẾN HÓA (EMA CONTINUAL LEARNING)
# =========================================================================

def _remember(items: list[str], value: str | None, limit: int) -> list[str]:
    """Thêm digest mới vào cuối danh sách (giữ thứ tự gần đây nhất), giới hạn kích thước."""
    if not value or _contains(items, value):
        return items
    return (items + [value])[-limit:]


def evolve(model: dict, obs: Observation, x: np.ndarray, settings: Settings) -> dict:
    """
    Áp dụng S_t = (1 - alpha) * S_{t-1} + alpha * X_t lên các chiều hành vi liên tục,
    đồng thời ghi nhớ thói quen / thiết bị / người thân / từ khóa mới của Chủ nhân.
    """
    alpha = settings.alpha
    model = dict(model)
    ref = np.asarray(model["vector"], dtype=float)
    for i in EVOLVING_DIMS:
        ref[i] = (1.0 - alpha) * ref[i] + alpha * x[i]
    model["vector"] = ref.round(6).tolist()

    keywords = Counter(model["keywords"])
    keywords.update(obs.keywords)
    model["keywords"] = dict(keywords.most_common(settings.max_keywords))

    model["pw_prefixes"] = _remember(list(model["pw_prefixes"]), obs.pw_prefix, settings.max_password_habits)
    model["pw_patterns"] = _remember(list(model["pw_patterns"]), obs.pw_pattern, settings.max_password_habits)
    model["devices"] = _remember(list(model["devices"]), obs.device, settings.max_trusted_devices)
    model["os_families"] = _remember(list(model["os_families"]), obs.os_family, settings.max_trusted_devices)

    family = list(model["family"])
    for d in sorted(obs.family):
        family = _remember(family, d, settings.max_family_members)
    model["family"] = family

    if obs.traits:
        model["traits"] = sorted(obs.traits)
    model["oauth"] = dict(model["oauth"])
    for p in OAUTH_PROVIDERS:
        if obs.oauth.get(p) and not model["oauth"].get(p):
            model["oauth"][p] = obs.oauth[p]  # liên kết thêm tài khoản mới
    return model


def evolve_radar(baseline: dict[str, float], current: dict[str, float], alpha: float) -> dict[str, float]:
    return {k: round((1.0 - alpha) * baseline.get(k, 0.0) + alpha * current.get(k, 0.0), 6) for k in current}
