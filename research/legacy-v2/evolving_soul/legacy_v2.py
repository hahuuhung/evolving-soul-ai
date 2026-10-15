"""
Đọc két sắt V2 và chấm điểm theo thuật toán V2 — CHỈ dùng cho migration V2 -> V3.

Két V2 (`vault/owner_soul_v2.enc`) được mã hóa bằng SHA-256 của một cụm từ, mặc định công khai trong mã nguồn,
nên coi như không được bảo vệ. Sau khi migrate, file V2 được đổi tên rồi xóa.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import uuid
from pathlib import Path

import numpy as np
from cryptography.fernet import Fernet, InvalidToken

from evolving_soul.errors import VaultCorruptError, VaultLockedError

V2_FILE = "owner_soul_v2.enc"
V2_DEFAULT_PHRASE = "chu_nhan_bi_mat_v2_2026"
V2_THRESHOLD = 0.72


def read_v2_profile(path: Path, phrase: str = V2_DEFAULT_PHRASE) -> dict:
    key = base64.urlsafe_b64encode(hashlib.sha256(phrase.encode("utf-8")).digest())
    try:
        raw = Fernet(key).decrypt(Path(path).read_bytes())
    except InvalidToken as exc:
        raise VaultLockedError("Sai cụm từ bí mật của két sắt V2.") from exc
    try:
        profile = json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise VaultCorruptError("Két sắt V2 hỏng.") from exc
    if "evolving_vector" not in profile:
        raise VaultCorruptError("File không phải hồ sơ V2.")
    return profile


# =========================================================================
# THUẬT TOÁN V2 (giữ nguyên hành vi của core_engine.EvolvingOwnerAI_V2)
# =========================================================================

def _hash_norm(text) -> float:
    if not text:
        return 0.0
    h = int(hashlib.sha256(str(text).strip().lower().encode("utf-8")).hexdigest()[:8], 16)
    return float((h % 10000) / 10000.0)


def _package(data: dict) -> tuple[np.ndarray, set[str], set[str]]:
    ids = [data.get("google", ""), data.get("apple", ""), data.get("facebook", "")]
    oauth = [_hash_norm(x) for x in ids] + [len([x for x in ids if x and str(x).strip()]) / 3.0]

    raw_tokens = str(data.get("family", "")).replace(",", " ").replace(";", " ").split()
    family_tokens = sorted(w.strip().lower() for w in raw_tokens if w.strip())
    traits = "".join(sorted(t.strip().lower() for t in data.get("traits", []) if t.strip()))
    lore = [_hash_norm(data.get("dob", "")), _hash_norm("".join(family_tokens)), _hash_norm(traits)]

    pw = str(data.get("password") or "")
    pw_struct = (0.3 * any(c.isupper() for c in pw) + 0.3 * any(c.isdigit() for c in pw)
                 + 0.4 * any(not c.isalnum() for c in pw))
    words = str(data.get("answer", "")).strip().lower().split()
    behav = [
        min(len(pw) / 20.0, 1.0), pw_struct, _hash_norm(pw[:3]) if len(pw) >= 3 else 0.0,
        _hash_norm(str(uuid.getnode())), _hash_norm(f"{platform.system()}_{platform.release()}"),
        min(float(np.mean([len(w) for w in words])) / 10.0, 1.0) if words else 0.0,
        _hash_norm("".join(sorted(set(words)))),
    ]
    return np.array(oauth + lore + behav, dtype=float), set(family_tokens), set(words)


def v2_trust_score(profile: dict, data: dict) -> float:
    """Điểm tin cậy V2: 0.55 cosine vector + 0.30 trí nhớ gia đình + 0.15 văn phong."""
    vec, family, words = _package(data)
    saved = np.asarray(profile["evolving_vector"], dtype=float)
    denom = float(np.linalg.norm(saved) * np.linalg.norm(vec))
    vec_sim = float(np.dot(saved, vec) / denom) if denom else 0.0
    saved_fam = set(profile.get("family_hashes", []))
    fam_sim = len({_hash_norm(w) for w in family} & saved_fam) / max(len(saved_fam), 1)
    saved_words = set(profile.get("cognitive_keywords", []))
    word_sim = len(words & saved_words) / max(len(saved_words), 1)
    return float(vec_sim * 0.55 + fam_sim * 0.30 + word_sim * 0.15)


def pending_legacy_summary(profile: dict) -> dict | None:
    """Thông tin di sản V2 để gợi ý Chủ nhân niêm phong lại (không mang theo hash 4 chữ số yếu)."""
    config = profile.get("legacy_config")
    if not config:
        return None
    return {
        "heir_name_display": config.get("heir_name_display", ""),
        "assets": list(config.get("digital_assets", [])),
        "message": config.get("legacy_message", ""),
        "inactivity_threshold_days": int(config.get("inactivity_threshold_days", 730)),
    }
