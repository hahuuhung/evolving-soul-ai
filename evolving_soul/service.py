"""
Lớp dịch vụ dùng chung cho các cổng giao tiếp (CLI, MCP Server, REST API).

Mỗi lời gọi từ bên ngoài là một "phiên" ngắn: mở engine, mở khóa két bằng EVOLVING_SOUL_PASSPHRASE,
thực hiện thao tác rồi trả về bản tóm tắt KHÔNG chứa dữ liệu nhạy cảm.
Thao tác nhạy cảm (niêm phong di sản, khởi tạo lại) bắt buộc kèm dữ liệu định danh của Chủ nhân
để xác minh ngay trong cùng phiên — không có cờ "đã xác minh" nào do bên gọi tự khai.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import os

from evolving_soul.config import AUTHOR_ATTRIBUTION, ENV_PASSPHRASE, Settings
from evolving_soul.engine import EvolvingSoulEngine
from evolving_soul.errors import OwnerNotVerifiedError, VaultLockedError, VaultNotFoundError
from evolving_soul.features import IDX_STYLE
from evolving_soul.scoring import PILLAR_LABELS

PASSPHRASE_HINT = f"Đặt biến môi trường {ENV_PASSPHRASE} bằng passphrase của Chủ nhân."


# =========================================================================
# MỞ ENGINE
# =========================================================================

def passphrase_from_env() -> str:
    passphrase = os.environ.get(ENV_PASSPHRASE, "")
    if not passphrase:
        raise VaultLockedError(f"Két sắt đang khóa. {PASSPHRASE_HINT}")
    return passphrase


def open_engine(unlock: bool = True, settings: Settings | None = None) -> EvolvingSoulEngine:
    """Tạo engine từ biến môi trường; unlock=True thì mở két bằng EVOLVING_SOUL_PASSPHRASE."""
    engine = EvolvingSoulEngine(settings or Settings.from_env())
    if unlock:
        if not engine.is_initialized:
            raise VaultNotFoundError("Chưa có két sắt. Hãy khởi tạo bằng `soul init` hoặc giao diện Streamlit.")
        engine.unlock(passphrase_from_env())
    return engine


def open_or_create_engine(settings: Settings | None = None) -> EvolvingSoulEngine:
    """Như open_engine, nhưng tạo két mới (bằng passphrase trong môi trường) nếu chưa có."""
    engine = EvolvingSoulEngine(settings or Settings.from_env())
    if engine.is_initialized:
        engine.unlock(passphrase_from_env())
    else:
        engine.create_vault(passphrase_from_env())
    return engine


def apply_demo_days(engine: EvolvingSoulEngine, days: float | None) -> None:
    """Mô phỏng số ngày offline — chỉ hợp lệ ở chế độ demo (ngoài demo ném PermissionError)."""
    if days:
        engine.set_demo_offset_days(float(days))


# =========================================================================
# CHUYỂN ĐỔI DỮ LIỆU VÀO / RA
# =========================================================================

def identity(
    *,
    google: str = "",
    apple: str = "",
    facebook: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] | None = None,
    password: str = "",
    answer: str = "",
    owner_name: str | None = None,
) -> dict:
    data = {
        "google": google or "", "apple": apple or "", "facebook": facebook or "", "dob": dob or "",
        "family": family or "", "traits": list(traits or []), "password": password or "", "answer": answer or "",
    }
    if owner_name is not None:
        data["owner_name"] = owner_name
    return data


def profile_summary(engine: EvolvingSoulEngine) -> dict:
    """Tóm tắt hồ sơ an toàn để hiển thị / trả về API (không có digest, vector hay tài sản)."""
    profile = engine.profile
    if profile is None:
        return {"status": "NOT_INITIALIZED", "is_initialized": False}
    return {
        "status": "MIGRATION_PENDING" if engine.migration_pending else "ACTIVE",
        "is_initialized": True,
        "owner_name": profile.get("owner_name"),
        "soul_id": engine.soul_id,
        "generation": profile.get("generation"),
        "created_at": profile.get("created_at"),
        "last_updated": profile.get("last_updated"),
        "traits": profile.get("traits_saved", []),
        "radar_metrics": profile.get("radar_baseline", {}),
        "legacy_status": engine.legacy_status(),
        "attribution": profile.get("author_attribution", AUTHOR_ATTRIBUTION),
    }


def verify_summary(result: dict) -> dict:
    return {
        "is_owner": result["is_owner"],
        "trust_score": round(result["trust_score"], 4),
        "threshold": result["threshold"],
        "gate_passed": result["gate_passed"],
        "pillars": {PILLAR_LABELS[p]: (None if v is None else round(v, 4)) for p, v in result["pillars"].items()},
        "current_generation": result["generation"],
        "owner_name": result["owner_name"],
        "migrated": result.get("migrated", False),
        "updated_radar": result["curr_radar"] if result["is_owner"] else None,
    }


def claim_summary(result: dict) -> dict:
    bio = result.get("bio")
    return {
        "is_verified": result["is_verified"],
        "is_unlockable": result["is_unlockable"],
        "is_unlocked": result["is_unlocked"],
        "knowledge_score": round(result["knowledge_score"], 4),
        "biometric": None if not bio else {"method": bio["method"], "assurance": bio["assurance"],
                                           "cosine": round(bio["cosine"], 4), "passed": bio["passed"]},
        "elapsed_days": result["elapsed_days"],
        "threshold_days": result["threshold_days"],
        "owner_name": result["owner_name"],
        "reason": result.get("reason", ""),
        "assets_unlocked": result["assets"] if result["is_unlocked"] else [],
        "legacy_message": result["message"] if result["is_unlocked"] else "Di sản số đang được bảo vệ an toàn.",
    }


# =========================================================================
# THAO TÁC NHẠY CẢM: XÁC MINH TRONG CÙNG PHIÊN
# =========================================================================

def verify_then(engine: EvolvingSoulEngine, owner_identity: dict) -> dict:
    """Xác minh Chủ nhân trong phiên hiện tại; ném OwnerNotVerifiedError nếu không đạt."""
    result = engine.verify_owner(owner_identity)
    if not result["is_owner"]:
        raise OwnerNotVerifiedError(
            f"Không xác minh được Chủ nhân (điểm tin cậy {result['trust_score']:.0%} < {result['threshold']:.0%})."
        )
    return result


def seal_legacy(engine: EvolvingSoulEngine, owner_identity: dict, **seal_args) -> dict:
    verify_then(engine, owner_identity)
    return engine.seal_legacy(**seal_args)


def register(engine: EvolvingSoulEngine, data: dict, force: bool = False, current_identity: dict | None = None) -> dict:
    """Đăng ký Gen #1. Ghi đè (force) yêu cầu dữ liệu định danh hiện tại của Chủ nhân để xác minh trước."""
    if engine.has_profile and force:
        if not current_identity:
            raise OwnerNotVerifiedError("Ghi đè hồ sơ cần dữ liệu định danh hiện tại của Chủ nhân để xác minh.")
        verify_then(engine, current_identity)
    return engine.register_owner(data, force=force)


# =========================================================================
# PERSONA PROMPT CHO AI AGENT
# =========================================================================

def _style_description(model: dict) -> str:
    word_len, sentence_len, punct = (model["vector"][i] for i in range(IDX_STYLE.start, IDX_STYLE.stop))
    words = "từ ngữ ngắn gọn, mộc mạc" if word_len < 0.35 else "từ ngữ dài, giàu hình ảnh"
    sentences = "câu ngắn, đi thẳng vào vấn đề" if sentence_len < 0.4 else "câu dài, diễn giải trọn ý"
    tone = "ít dấu câu, giọng trầm tĩnh" if punct < 0.15 else "dùng dấu câu nhiều, giọng giàu cảm xúc"
    return f"{words}; {sentences}; {tone}"


def persona_prompt(engine: EvolvingSoulEngine) -> str:
    """
    System Prompt mô tả bản sắc Chủ nhân cho AI Agent.
    V3 không còn lưu từ khóa dạng rõ (chỉ HMAC), nên văn phong được mô tả từ các đặc trưng thống kê đã tiến hóa.
    """
    profile = engine.profile
    if not profile or "model" not in profile:
        return ("Bạn là trợ lý AI thuộc hệ thống Evolving Soul AI. "
                "Hiện chưa có hồ sơ Chủ nhân hoàn chỉnh trong két sắt.")
    owner = profile.get("owner_name", "Chủ nhân")
    generation = profile.get("generation", 1)
    traits = ", ".join(profile.get("traits_saved", [])) or "chưa khai báo"
    return (
        f"# BẢN SẮC TÂM HỒN & NHÂN CÁCH CHỦ NHÂN (EVOLVING SOUL PERSONA — GEN #{generation})\n"
        f"- Chủ nhân: {owner}\n"
        f"- Bản quyền & Sáng lập: {profile.get('author_attribution', AUTHOR_ATTRIBUTION)}\n"
        f"- Thế hệ tiến hóa: #{generation} (thích nghi liên tục bằng EMA α=0.15)\n"
        f"- Nét cá tính cốt lõi: {traits}\n"
        f"- Văn phong (Stylometry): {_style_description(profile['model'])}\n\n"
        "## NGUYÊN TẮC HÀNH XỬ DÀNH CHO AI AGENT:\n"
        f"1. Trung thành với bản sắc của Chủ nhân ({owner}); phản hồi theo văn phong và cá tính ở trên.\n"
        "2. Tuân thủ Zero-Knowledge: không bao giờ hỏi, suy đoán hay tiết lộ ngày sinh, tên người thân, mật khẩu, "
        "mật ước gia đình hoặc passphrase két sắt.\n"
        "3. Không tự nhận là Chủ nhân và không thay Chủ nhân xác minh danh tính.\n"
        "4. Khi người thừa kế được hệ thống xác thực hợp lệ sau thời hạn vắng mặt, đồng hành và hướng dẫn họ "
        "tiếp quản di sản số một cách tôn nghiêm."
    )
