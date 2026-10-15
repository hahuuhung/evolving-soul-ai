"""
Model Context Protocol (MCP) Server — Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Cung cấp giao diện chuẩn MCP (Model Context Protocol) 2.x cho Claude Desktop, Antigravity IDE, Cursor
và các hệ thống AI Agents bên ngoài liên kết, thẩm định danh tính và đồng hành cùng Evolving Soul AI.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer
from core_engine import EvolvingOwnerAI_V2

# Thiết lập Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [SoulMCP] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr  # Quan trọng: stdio transport dùng stdout cho JSON-RPC, log phải ra stderr!
)
logger = logging.getLogger("soul_mcp")

# Khởi tạo MCP Server
mcp = MCPServer("evolving-soul-ai")


def get_engine() -> EvolvingOwnerAI_V2:
    """Khởi tạo engine dựa trên biến môi trường hoặc cấu hình mặc định."""
    vault_dir = os.environ.get("EVOLVING_SOUL_VAULT_DIR", "vault")
    secret_key = os.environ.get("EVOLVING_SOUL_PASSPHRASE", "chu_nhan_bi_mat_v2_2026")
    demo_mode = os.environ.get("EVOLVING_SOUL_DEMO", "") == "1"
    return EvolvingOwnerAI_V2(secret_key_phrase=secret_key, vault_dir=vault_dir, demo_mode=demo_mode)


# =========================================================================
# MCP RESOURCES (TÀI NGUYÊN THỜI GIAN THỰC)
# =========================================================================

@mcp.resource("soul://profile")
def resource_profile() -> str:
    """Tài nguyên hồ sơ định danh số hiện tại của Chủ nhân (Gen, thời gian cập nhật)."""
    engine = get_engine()
    profile = engine.load_profile()
    if not profile:
        return json.dumps({"status": "NOT_INITIALIZED", "message": "Chưa khởi tạo hồ sơ chủ nhân."}, ensure_ascii=False)
    summary = {
        "owner_name": profile.get("owner_name"),
        "generation": profile.get("generation"),
        "created_at": profile.get("created_at"),
        "last_updated": profile.get("last_updated"),
        "author_attribution": profile.get("author_attribution"),
        "traits": profile.get("traits_saved", []),
        "radar_baseline": profile.get("radar_baseline", {})
    }
    return json.dumps(summary, indent=2, ensure_ascii=False)


@mcp.resource("soul://radar")
def resource_radar() -> str:
    """Tài nguyên 5 trụ cột đặc trưng radar thời gian thực của Chủ nhân."""
    engine = get_engine()
    profile = engine.load_profile()
    if not profile:
        return json.dumps({"status": "NOT_INITIALIZED"}, ensure_ascii=False)
    return json.dumps(profile.get("radar_baseline", {}), indent=2, ensure_ascii=False)


@mcp.resource("soul://persona")
def resource_persona() -> str:
    """Tài nguyên Prompt System đúc kết từ bản sắc, văn phong và cá tính của Chủ nhân."""
    engine = get_engine()
    return engine.generate_persona_prompt()


@mcp.resource("soul://legacy")
def resource_legacy() -> str:
    """Tài nguyên trạng thái Dead Man's Switch (ngưỡng 730 ngày) và người thừa kế."""
    engine = get_engine()
    status = engine.check_inactivity_status()
    if not status:
        return json.dumps({"status": "NOT_CONFIGURED", "message": "Chưa thiết lập di sản số."}, ensure_ascii=False)
    return json.dumps(status, indent=2, ensure_ascii=False)


# =========================================================================
# MCP TOOLS (CÔNG CỤ TÁC VỤ DÀNH CHO AI AGENTS)
# =========================================================================

@mcp.tool()
def soul_get_status() -> dict[str, Any]:
    """
    Tra cứu trạng thái tổng quan của Evolving Soul AI:
    Bao gồm tên chủ nhân, thế hệ tiến hóa (Gen), 5 trụ cột radar và đồng hồ di sản số.
    """
    engine = get_engine()
    profile = engine.load_profile()
    if not profile:
        return {
            "status": "NOT_INITIALIZED",
            "is_initialized": False,
            "message": "Két sắt chưa có hồ sơ chủ nhân. Hãy dùng lệnh soul_register để khởi tạo."
        }

    legacy_status = engine.check_inactivity_status()
    return {
        "status": "ACTIVE",
        "is_initialized": True,
        "owner_name": profile.get("owner_name"),
        "generation": profile.get("generation"),
        "created_at": profile.get("created_at"),
        "last_updated": profile.get("last_updated"),
        "radar_metrics": profile.get("radar_baseline", {}),
        "traits": profile.get("traits_saved", []),
        "legacy_status": legacy_status,
        "attribution": profile.get("author_attribution")
    }


@mcp.tool()
def soul_verify_identity(
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] = [],
    password_sample: str = "",
    security_answer: str = ""
) -> dict[str, Any]:
    """
    Xác minh danh tính người đang tương tác với AI theo nguyên tắc Zero-Knowledge:
    Kiểm tra 5 trụ cột đặc trưng (OAuth, Tri thức gia đình, Phong cách ngôn ngữ, Thói quen mật khẩu, Thiết bị).
    Trả về điểm tin cậy (Trust Score) và xác nhận is_owner.
    """
    engine = get_engine()
    data = {
        "google": google_id,
        "apple": apple_id,
        "facebook": facebook_id,
        "dob": dob,
        "family": family,
        "traits": traits,
        "password": password_sample,
        "answer": security_answer
    }
    result = engine.verify_and_evolve(data)
    if not result:
        return {"status": "ERROR", "message": "Không thể xác minh, két sắt chưa được khởi tạo."}

    return {
        "is_owner": result["is_owner"],
        "trust_score": round(result["trust_score"], 4),
        "vec_similarity": round(result["vec_sim"], 4),
        "family_match": round(result["fam_sim"], 4),
        "stylometry_match": round(result["word_sim"], 4),
        "current_generation": result["generation"],
        "owner_name": result["owner_name"]
    }


@mcp.tool()
def soul_evolve(
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] = [],
    password_sample: str = "",
    security_answer: str = ""
) -> dict[str, Any]:
    """
    Kích hoạt chu kỳ học liên tục EMA (Exponential Moving Average) để Soul AI tự thích nghi với Chủ nhân.
    Nếu điểm tin cậy đạt chuẩn, hệ thống tự động cập nhật vector đặc trưng và tăng lên Gen #N+1.
    """
    engine = get_engine()
    data = {
        "google": google_id,
        "apple": apple_id,
        "facebook": facebook_id,
        "dob": dob,
        "family": family,
        "traits": traits,
        "password": password_sample,
        "answer": security_answer
    }
    result = engine.verify_and_evolve(data)
    if not result:
        return {"status": "ERROR", "message": "Két sắt chưa được khởi tạo."}

    if result["is_owner"]:
        return {
            "status": "EVOLVED",
            "message": f"Chủ nhân đã được xác nhận. Hồ sơ đã tự động tiến hóa lên Thế hệ Gen #{result['generation']}!",
            "new_generation": result["generation"],
            "trust_score": round(result["trust_score"], 4),
            "updated_radar": result["curr_radar"]
        }
    else:
        return {
            "status": "REJECTED",
            "message": f"Điểm tin cậy ({result['trust_score']:.2f}) chưa đạt ngưỡng an toàn (0.72). Không tiến hóa.",
            "is_owner": False,
            "trust_score": round(result["trust_score"], 4)
        }


@mcp.tool()
def soul_register(
    owner_name: str,
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] = [],
    password_sample: str = "",
    security_answer: str = "",
    force_override: bool = False
) -> dict[str, Any]:
    """
    Khởi tạo 'Hạt giống Số' (Generation #1) của Chủ nhân trong két sắt bảo mật.
    Nếu hồ sơ đã tồn tại, cần force_override=True để ghi đè.
    """
    engine = get_engine()
    data = {
        "owner_name": owner_name,
        "google": google_id,
        "apple": apple_id,
        "facebook": facebook_id,
        "dob": dob,
        "family": family,
        "traits": traits,
        "password": password_sample,
        "answer": security_answer
    }
    try:
        profile = engine.register_owner(data, force=force_override)
        return {
            "status": "REGISTERED",
            "message": f"Đã khởi tạo thành công Hạt giống Số cho Chủ nhân: {profile['owner_name']} (Gen #1)",
            "generation": 1,
            "created_at": profile["created_at"],
            "radar_baseline": profile["radar_baseline"]
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


@mcp.tool()
def soul_legacy_status(simulated_days_offline: float = 0.0) -> dict[str, Any]:
    """
    Kiểm tra trạng thái đếm ngược của Giao thức Thừa kế Di sản Số (Dead Man's Switch 2 năm / 730 ngày).
    """
    engine = get_engine()
    status = engine.check_inactivity_status(simulated_days_offline=simulated_days_offline)
    if not status:
        return {"status": "NOT_CONFIGURED", "message": "Chưa thiết lập Di sản Số trong két sắt."}

    return {
        "status": "OK",
        "elapsed_days": status["elapsed_days"],
        "threshold_days": status["threshold_days"],
        "is_unlockable": status["is_unlockable"],
        "has_biometric_lock": status["has_biometric_lock"],
        "heir_name": status["heir_name_display"],
        "inheritance_claimed": status["inheritance_claimed"]
    }


@mcp.tool()
def soul_claim_legacy(
    kin_name: str,
    kin_email: str,
    owner_dob: str,
    other_family_members: str,
    family_secret: str,
    simulated_days_offline: float = 0.0
) -> dict[str, Any]:
    """
    Xác thực khẩn cấp Người thừa kế (Tri thức Gia đình + Mật ước) để mở khóa Di sản Số.
    Lưu ý: Chỉ mở khóa khi Chủ nhân đã vắng mặt >= 730 ngày (2 năm).
    """
    engine = get_engine()
    res = engine.verify_kin_with_biometrics(
        kin_name=kin_name,
        kin_email=kin_email,
        owner_dob=owner_dob,
        other_family_members=other_family_members,
        family_secret_input=family_secret,
        live_bio_bytes=None,
        simulated_days_offline=simulated_days_offline
    )
    if res.get("status") == "ERROR":
        return res

    return {
        "is_verified": res["is_verified"],
        "is_unlocked": res["is_unlocked"],
        "knowledge_score": round(res["knowledge_score"], 4),
        "elapsed_days": res["elapsed_days"],
        "threshold_days": res["threshold_days"],
        "owner_name": res["owner_name"],
        "assets_unlocked": res.get("assets", []) if res["is_unlocked"] else [],
        "legacy_message": res.get("message", "") if res["is_unlocked"] else "Di sản số đang được bảo vệ an toàn."
    }


@mcp.tool()
def soul_get_persona_prompt() -> str:
    """
    Tạo ra System Prompt mang toàn bộ phong cách ngôn ngữ, cá tính và giá trị cốt lõi của Chủ nhân
    để AI Agent tích hợp vào ngữ cảnh hội thoại, trở thành người đồng hành thấu hiểu nhất.
    """
    engine = get_engine()
    return engine.generate_persona_prompt()


# =========================================================================
# MCP PROMPT TEMPLATES
# =========================================================================

@mcp.prompt("soul_companion")
def prompt_soul_companion() -> str:
    """Prompt thiết lập nhân cách AI Agent đồng hành mang bản sắc Evolving Soul của Chủ nhân."""
    engine = get_engine()
    return engine.generate_persona_prompt()


# =========================================================================
# ENTRYPOINT CHẠY SERVER
# =========================================================================

def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None:
    """Khởi động MCP Server với giao thức stdio hoặc SSE."""
    logger.info("Khởi động Evolving Soul AI MCP Server [Transport: %s]...", transport)
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info("Lắng nghe kết nối SSE tại http://%s:%d/sse", host, port)
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise ValueError(f"Transport không được hỗ trợ: {transport}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evolving Soul AI — MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Phương thức truyền thông MCP (stdio / sse)")
    parser.add_argument("--host", default="127.0.0.1", help="Địa chỉ host khi chạy SSE")
    parser.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe khi chạy SSE")
    args = parser.parse_args()

    run_server(transport=args.transport, host=args.host, port=args.port)
