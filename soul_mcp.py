"""
Model Context Protocol (MCP) Server — Evolving Soul AI V3
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Cung cấp giao diện chuẩn MCP 2.x (Python ≥ 3.10) cho Claude Desktop, Antigravity IDE, Cursor và các AI Agent.
Két sắt được mở bằng biến môi trường EVOLVING_SOUL_PASSPHRASE (không có giá trị mặc định).
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer

from evolving_soul import EvolvingSoulError, service
from evolving_soul.logging_setup import configure_logging

# Log ra stderr: stdio transport dùng stdout cho JSON-RPC
configure_logging()
logger = logging.getLogger("evolving_soul.mcp")

mcp = MCPServer("evolving-soul-ai")


def _safe(action: Callable[[], Any]) -> Any:
    """Chuyển lỗi nghiệp vụ thành phản hồi có cấu trúc thay vì để MCP trả traceback."""
    try:
        return action()
    except (EvolvingSoulError, PermissionError, ValueError) as exc:
        logger.warning("mcp_tool_error type=%s", type(exc).__name__)
        return {"status": "ERROR", "error_type": type(exc).__name__, "message": str(exc)}


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


# =========================================================================
# MCP RESOURCES (TÀI NGUYÊN THỜI GIAN THỰC)
# =========================================================================

@mcp.resource("soul://profile")
def resource_profile() -> str:
    """Hồ sơ định danh số hiện tại của Chủ nhân (Gen, Soul ID, cá tính, radar) — không chứa dữ liệu nhạy cảm."""
    return _json(_safe(lambda: service.profile_summary(service.open_engine())))


@mcp.resource("soul://radar")
def resource_radar() -> str:
    """5 trụ cột đặc trưng radar (chữ ký gốc đã tiến hóa bằng EMA)."""
    summary = _safe(lambda: service.profile_summary(service.open_engine()))
    return _json(summary.get("radar_metrics", summary))


@mcp.resource("soul://persona")
def resource_persona() -> str:
    """System Prompt đúc kết từ bản sắc, văn phong và cá tính của Chủ nhân."""
    result = _safe(lambda: service.persona_prompt(service.open_engine()))
    return result if isinstance(result, str) else _json(result)


@mcp.resource("soul://legacy")
def resource_legacy() -> str:
    """Trạng thái Dead Man's Switch (ngưỡng mặc định 730 ngày)."""
    status = _safe(lambda: service.open_engine().legacy_status())
    return _json(status or {"status": "NOT_CONFIGURED", "message": "Chưa niêm phong Di sản Số."})


# =========================================================================
# MCP TOOLS (CÔNG CỤ TÁC VỤ DÀNH CHO AI AGENTS)
# =========================================================================

@mcp.tool()
def soul_get_status() -> dict[str, Any]:
    """Trạng thái tổng quan: tên Chủ nhân, Soul ID, thế hệ tiến hóa, 5 trụ cột radar và đồng hồ di sản số."""
    return _safe(lambda: service.profile_summary(service.open_engine()))


@mcp.tool()
def soul_verify_identity(
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] | None = None,
    password_sample: str = "",
    security_answer: str = "",
) -> dict[str, Any]:
    """
    Xác minh người đang tương tác có phải Chủ nhân (Zero-Knowledge, 5 trụ cột).
    Nếu đạt, hồ sơ tự tiến hóa lên Gen #N+1 (EMA). Sai 5 lần liên tiếp sẽ bị khóa tạm.
    """
    data = service.identity(google=google_id, apple=apple_id, facebook=facebook_id, dob=dob, family=family,
                            traits=traits, password=password_sample, answer=security_answer)
    return _safe(lambda: service.verify_summary(service.open_engine().verify_owner(data)))


@mcp.tool()
def soul_evolve(
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] | None = None,
    password_sample: str = "",
    security_answer: str = "",
) -> dict[str, Any]:
    """Chu kỳ học liên tục EMA: xác minh Chủ nhân và tiến hóa hồ sơ (tương đương soul_verify_identity)."""
    result = soul_verify_identity(google_id, apple_id, facebook_id, dob, family, traits, password_sample, security_answer)
    if result.get("status") == "ERROR":
        return result
    if result["is_owner"]:
        return {"status": "EVOLVED", "new_generation": result["current_generation"],
                "trust_score": result["trust_score"], "updated_radar": result["updated_radar"],
                "message": f"Chủ nhân đã được xác nhận. Hồ sơ tiến hóa lên Gen #{result['current_generation']}."}
    return {"status": "REJECTED", "is_owner": False, "trust_score": result["trust_score"],
            "message": f"Điểm tin cậy {result['trust_score']:.0%} chưa đạt ngưỡng {result['threshold']:.0%}. Không tiến hóa."}


@mcp.tool()
def soul_register(
    owner_name: str,
    google_id: str = "",
    apple_id: str = "",
    facebook_id: str = "",
    dob: str = "",
    family: str = "",
    traits: list[str] | None = None,
    password_sample: str = "",
    security_answer: str = "",
    force_override: bool = False,
    current_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Khởi tạo 'Hạt giống Số' (Gen #1). Tạo két mới bằng EVOLVING_SOUL_PASSPHRASE nếu chưa có.
    Ghi đè hồ sơ đã có cần force_override=True VÀ current_identity (dữ liệu định danh hiện tại của Chủ nhân
    với các khóa google/apple/facebook/dob/family/traits/password/answer) để xác minh trước.
    """
    data = service.identity(google=google_id, apple=apple_id, facebook=facebook_id, dob=dob, family=family,
                            traits=traits, password=password_sample, answer=security_answer, owner_name=owner_name)

    def run() -> dict[str, Any]:
        profile = service.register(service.open_or_create_engine(), data, force=force_override,
                                   current_identity=current_identity)
        return {"status": "REGISTERED", "generation": 1, "created_at": profile["created_at"],
                "radar_baseline": profile["radar_baseline"],
                "message": f"Đã khởi tạo Hạt giống Số cho Chủ nhân: {profile['owner_name']} (Gen #1)"}

    return _safe(run)


@mcp.tool()
def soul_legacy_status(simulated_days_offline: float = 0.0) -> dict[str, Any]:
    """Đồng hồ đếm ngược Dead Man's Switch. simulated_days_offline chỉ dùng được ở chế độ demo."""
    def run() -> dict[str, Any]:
        engine = service.open_engine()
        service.apply_demo_days(engine, simulated_days_offline)
        status = engine.legacy_status()
        return {"status": "OK", **status} if status else {"status": "NOT_CONFIGURED", "message": "Chưa niêm phong Di sản Số."}

    return _safe(run)


@mcp.tool()
def soul_claim_legacy(
    kin_name: str,
    kin_email: str,
    owner_dob: str,
    other_family_members: str,
    family_secret: str,
    simulated_days_offline: float = 0.0,
) -> dict[str, Any]:
    """
    Người thừa kế xác thực (tri thức gia đình + mật ước) để mở khóa Di sản Số — không cần passphrase của Chủ nhân.
    Chỉ bàn giao khi Chủ nhân vắng mặt đủ ngưỡng. Di sản có khóa sinh trắc phải tiếp quản qua giao diện Streamlit.
    """
    def run() -> dict[str, Any]:
        engine = service.open_engine(unlock=False)
        service.apply_demo_days(engine, simulated_days_offline)
        return service.claim_summary(engine.claim_legacy(
            kin_name=kin_name, kin_email=kin_email, owner_dob=owner_dob, family_members=other_family_members,
            family_secret=family_secret,
        ))

    return _safe(run)


@mcp.tool()
def soul_get_persona_prompt() -> str:
    """System Prompt mang phong cách, cá tính và giá trị cốt lõi của Chủ nhân để AI Agent đồng hành."""
    return resource_persona()


# =========================================================================
# MCP PROMPT TEMPLATES
# =========================================================================

@mcp.prompt("soul_companion")
def prompt_soul_companion() -> str:
    """Prompt thiết lập nhân cách AI Agent đồng hành mang bản sắc Evolving Soul của Chủ nhân."""
    return resource_persona()


# =========================================================================
# ENTRYPOINT CHẠY SERVER
# =========================================================================

def run_server(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> None:
    """Khởi động MCP Server với giao thức stdio hoặc SSE."""
    logger.info("mcp_server_start transport=%s", transport)
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        logger.info("mcp_sse_listen url=http://%s:%d/sse", host, port)
        mcp.run(transport="sse", host=host, port=port)
    else:
        raise ValueError(f"Transport không được hỗ trợ: {transport}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evolving Soul AI — MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Phương thức truyền thông MCP")
    parser.add_argument("--host", default="127.0.0.1", help="Địa chỉ host khi chạy SSE")
    parser.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe khi chạy SSE")
    args = parser.parse_args()
    run_server(transport=args.transport, host=args.host, port=args.port)
