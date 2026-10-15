"""
Giao thức Di sản Số — Dead Man's Switch (V3).

- < ngưỡng (mặc định 730 ngày) kể từ lần cuối Chủ nhân xác minh thành công: tài sản khóa, người thân ở chế độ đồng hành.
- ≥ 90% ngưỡng: trạng thái cảnh báo để nhắc Chủ nhân xác minh.
- ≥ ngưỡng: người thừa kế được xác thực kép (tri thức gia đình + sinh trắc học) để nhận tài sản.
- Chủ nhân quay lại và xác minh thành công -> heartbeat; nếu di sản đã được tiếp quản thì thu hồi.

Danh mục tài sản + lời nhắn được mã hóa thêm một lớp bằng khóa suy từ mật ước gia đình, nên người chỉ có
passphrase của Chủ nhân (ví dụ dùng chung máy) cũng không đọc được.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import base64
import json

from evolving_soul import crypto
from evolving_soul.config import Settings
from evolving_soul.crypto import SoulCipher, digests_equal, strip_diacritics
from evolving_soul.features import parse_family_names

SECONDS_PER_DAY = 86400.0
MIN_FAMILY_SECRET_LENGTH = 10

# Trọng số điểm tri thức của người thừa kế (mật ước đã được chứng minh khi mở bọc khóa)
KIN_WEIGHTS = {"name": 0.20, "email": 0.20, "dob": 0.15, "family": 0.20, "secret": 0.25}


def seal(
    cipher: SoulCipher,
    settings: Settings,
    *,
    heir_name: str,
    heir_email: str,
    family_secret: str,
    assets: list[str],
    message: str,
    biometric: dict | None,
    inactivity_days: int,
    now: float,
) -> dict:
    """Tạo cấu hình di sản (nằm trong hồ sơ đã mã hóa)."""
    payload_salt = crypto.new_salt()
    payload = json.dumps({"assets": assets, "message": message}, ensure_ascii=False).encode("utf-8")
    return {
        "heir_name_display": heir_name,
        "heir_name": cipher.digest(strip_diacritics(heir_name), "heir:name"),
        "heir_email": cipher.digest(heir_email, "heir:email"),
        "inactivity_threshold_days": int(inactivity_days),
        "sealed_at": now,
        "last_owner_ping": now,
        "biometric": biometric,
        "asset_count": len(assets),
        "payload_salt": base64.b64encode(payload_salt).decode("ascii"),
        "payload_n": settings.kdf_n,
        "payload": crypto.encrypt_with_secret(payload, family_secret, payload_salt, settings.kdf_n),
        "claimed": False,
        "custodian_display": None,
        "claimed_at": None,
    }


def open_payload(legacy: dict, family_secret: str) -> dict:
    salt = base64.b64decode(legacy["payload_salt"])
    raw = crypto.decrypt_with_secret(legacy["payload"], family_secret, salt, int(legacy["payload_n"]))
    return json.loads(raw.decode("utf-8"))


def status(legacy: dict, now: float, settings: Settings) -> dict:
    threshold = int(legacy.get("inactivity_threshold_days", settings.inactivity_days))
    elapsed = max(0.0, (now - float(legacy["last_owner_ping"])) / SECONDS_PER_DAY)
    return {
        "elapsed_days": round(elapsed, 1),
        "threshold_days": threshold,
        "remaining_days": round(max(0.0, threshold - elapsed), 1),
        "is_unlockable": elapsed >= threshold,
        "warning": elapsed >= threshold * settings.warning_ratio,
        "has_biometric_lock": legacy.get("biometric") is not None,
        "biometric_method": (legacy.get("biometric") or {}).get("method"),
        "heir_name_display": legacy.get("heir_name_display"),
        "asset_count": legacy.get("asset_count", 0),
        "claimed": bool(legacy.get("claimed")),
    }


def heartbeat(legacy: dict, now: float) -> bool:
    """Chủ nhân còn hoạt động: đặt lại đồng hồ; thu hồi nếu di sản đã bị tiếp quản. Trả về True nếu đã thu hồi."""
    legacy["last_owner_ping"] = now
    if legacy.get("claimed"):
        legacy["claimed"] = False
        legacy["custodian_display"] = None
        legacy["claimed_at"] = None
        return True
    return False


def knowledge_score(
    legacy: dict,
    model: dict,
    cipher: SoulCipher,
    *,
    kin_name: str,
    kin_email: str,
    owner_dob: str,
    family_members: str,
) -> tuple[float, dict]:
    """Điểm tri thức gia đình của người thừa kế. Mật ước đã đúng (nếu không thì không mở được két)."""
    saved_family = list(model.get("family", []))
    given = {cipher.digest(n, "family") for n in parse_family_names(family_members)}
    matched = sum(1 for d in given if any(digests_equal(d, s) for s in saved_family))
    needed = max(1, min(3, len(saved_family)))
    parts = {
        "name": 1.0 if digests_equal(legacy["heir_name"], cipher.digest(strip_diacritics(kin_name), "heir:name")) else 0.0,
        "email": 1.0 if digests_equal(legacy["heir_email"], cipher.digest(kin_email, "heir:email")) else 0.0,
        "dob": 1.0 if digests_equal(model.get("dob"), cipher.digest(owner_dob, "dob")) else 0.0,
        "family": min(1.0, matched / needed),
        "secret": 1.0,
    }
    return float(sum(KIN_WEIGHTS[k] * v for k, v in parts.items())), parts


def decide(knowledge: float, bio: dict | None, has_biometric_lock: bool, settings: Settings) -> tuple[bool, str]:
    """
    Quy tắc xác thực kép:
      - Có mẫu SFace (bảo đảm cao): tri thức ≥ 0.70 VÀ sinh trắc khớp.
      - Mẫu histogram (bảo đảm thấp): tri thức ≥ 0.85 VÀ sinh trắc khớp.
      - Không niêm phong sinh trắc: tri thức ≥ 0.85.
    """
    if not has_biometric_lock:
        ok = knowledge >= settings.kin_knowledge_threshold_no_bio
        return ok, "" if ok else f"Điểm tri thức cần ≥ {settings.kin_knowledge_threshold_no_bio:.0%} khi không có lớp sinh trắc."
    if bio is None:
        return False, "Cần quét sinh trắc học người thừa kế."
    required = settings.kin_knowledge_threshold if bio["assurance"] == "high" else settings.kin_knowledge_threshold_no_bio
    if knowledge < required:
        return False, f"Điểm tri thức gia đình chưa đạt {required:.0%}."
    if not bio["passed"]:
        return False, "Sinh trắc học không khớp với mẫu đã niêm phong."
    return True, ""
