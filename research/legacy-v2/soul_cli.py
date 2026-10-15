"""
Giao Diện Dòng Lệnh Chuyên Nghiệp (Rich CLI) — Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Cung cấp các lệnh trực quan dòng lệnh (CLI) với bảng biểu màu sắc, thanh tiến độ radar,
hỗ trợ cờ --json cho tự động hóa và tích hợp trực tiếp lệnh khởi chạy MCP Server & REST API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import BarColumn, Progress, TextColumn

from core_engine import EvolvingOwnerAI_V2

console = Console()
err_console = Console(stderr=True)


def get_engine() -> EvolvingOwnerAI_V2:
    """Lấy thể hiện EvolvingOwnerAI_V2 từ cấu hình môi trường."""
    vault_dir = os.environ.get("EVOLVING_SOUL_VAULT_DIR", "vault")
    secret_key = os.environ.get("EVOLVING_SOUL_PASSPHRASE", "chu_nhan_bi_mat_v2_2026")
    demo_mode = os.environ.get("EVOLVING_SOUL_DEMO", "") == "1"
    return EvolvingOwnerAI_V2(secret_key_phrase=secret_key, vault_dir=vault_dir, demo_mode=demo_mode)


def print_banner() -> None:
    """Hiển thị biểu ngữ nhận diện thương hiệu Evolving Soul AI."""
    banner_text = Text()
    banner_text.append("🛡️  EVOLVING SOUL AI — HỆ THỐNG ĐỊNH DANH SỐ & TIẾN HÓA\n", style="bold cyan")
    banner_text.append("Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X\n", style="bold green")
    banner_text.append("Chuẩn bảo mật Zero-Knowledge • 5 Trụ Cột Radar • Dead Man's Switch 2 Năm", style="dim")
    console.print(Panel(banner_text, border_style="bright_blue", expand=False))


# =========================================================================
# LỆNH: STATUS (TRẠNG THÁI HỒ SƠ)
# =========================================================================

def cmd_status(args: argparse.Namespace) -> None:
    engine = get_engine()
    profile = engine.load_profile()

    if not profile:
        if args.json:
            print(json.dumps({"status": "NOT_INITIALIZED", "is_initialized": False}, ensure_ascii=False))
        else:
            print_banner()
            err_console.print("[yellow]⚠️  Két sắt chưa có hồ sơ chủ nhân.[/yellow] Sử dụng lệnh [bold cyan]soul init[/bold cyan] để khởi tạo.")
        return

    legacy_status = engine.check_inactivity_status()
    radar = profile.get("radar_baseline", {})

    if args.json:
        payload = {
            "status": "INITIALIZED",
            "owner_name": profile.get("owner_name"),
            "generation": profile.get("generation"),
            "created_at": profile.get("created_at"),
            "last_updated": profile.get("last_updated"),
            "traits": profile.get("traits_saved", []),
            "radar_metrics": radar,
            "legacy_status": legacy_status,
            "author_attribution": profile.get("author_attribution")
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print_banner()

    # Bảng thông tin định danh
    info_table = Table(title="📋 THÔNG TIN CHỦ NHÂN & THẾ HỆ", border_style="cyan", show_header=False)
    info_table.add_column("Thuộc tính", style="bold white", width=24)
    info_table.add_column("Giá trị", style="green")

    info_table.add_row("Chủ nhân", profile.get("owner_name", "N/A"))
    info_table.add_row("Thế hệ Tiến hóa", f"Gen #{profile.get('generation', 1)} (Đang tự thích nghi)")
    info_table.add_row("Thời gian khởi tạo", profile.get("created_at", "N/A"))
    info_table.add_row("Cập nhật gần nhất", profile.get("last_updated", "N/A"))
    info_table.add_row("Nét cá tính đã lưu", ", ".join(profile.get("traits_saved", [])) or "Chưa cấu hình")
    console.print(info_table)

    # Bảng 5 Trụ Cột Radar với thanh tiến độ
    radar_table = Table(title="📊 5 TRỤ CỘT ĐẶC TRƯNG CHỦ NHÂN (RADAR METRICS)", border_style="bright_blue")
    radar_table.add_column("Trụ Cột Đặc Trưng", style="bold white", width=32)
    radar_table.add_column("Điểm Số", justify="right", style="cyan", width=12)
    radar_table.add_column("Thanh Trực Quan", width=30)

    for pillar, val in radar.items():
        pct = max(0.0, min(float(val), 1.0)) * 100.0
        bar_len = int(pct / 5)
        bar_str = "█" * bar_len + "░" * (20 - bar_len)
        color = "green" if pct >= 70 else "yellow" if pct >= 40 else "red"
        radar_table.add_row(pillar, f"{pct:5.1f}%", f"[{color}]{bar_str}[/{color}]")

    console.print(radar_table)

    # Khung di sản số
    if legacy_status:
        leg_text = Text()
        status_color = "red" if legacy_status.get("is_unlockable") else "green"
        leg_text.append(f"• Người thừa kế: {legacy_status.get('heir_name_display', 'N/A')}\n", style="bold")
        leg_text.append(f"• Thời gian vắng mặt: {legacy_status.get('elapsed_days', 0):.1f} / {legacy_status.get('threshold_days', 730)} ngày\n")
        leg_text.append(f"• Trạng thái khóa: [{'MỞ KHÓA KHẨN CẤP' if legacy_status.get('is_unlockable') else 'ĐANG BẢO VỆ CHỦ NHÂN'}]\n", style=status_color)
        leg_text.append(f"• Khóa Sinh trắc học khẩn cấp: {'ĐÃ THIẾT LẬP (64-D)' if legacy_status.get('has_biometric_lock') else 'KHÔNG SỬ DỤNG'}")
        console.print(Panel(leg_text, title="⏳ GIAO THỨC DI SẢN SỐ (DEAD MAN'S SWITCH)", border_style="gold1"))


# =========================================================================
# LỆNH: VERIFY (XÁC MINH DANH TÍNH)
# =========================================================================

def cmd_verify(args: argparse.Namespace) -> None:
    engine = get_engine()

    data: dict[str, Any] = {}
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "google": args.google or "",
            "apple": args.apple or "",
            "facebook": args.facebook or "",
            "dob": args.dob or "",
            "family": args.family or "",
            "traits": [t.strip() for t in args.traits.split(",") if t.strip()] if args.traits else [],
            "password": args.password or "",
            "answer": args.answer or ""
        }

    res = engine.verify_and_evolve(data)
    if not res:
        err_console.print("[red]❌ Két sắt chưa có hồ sơ hoặc xảy ra lỗi.[/red]")
        sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    print_banner()
    is_owner = res["is_owner"]
    badge_style = "bold white on green" if is_owner else "bold white on red"
    badge_text = " ✅ XÁC MINH THÀNH CÔNG — CHÍNH CHỦ " if is_owner else " ❌ TỪ CHỐI — KHÔNG KHỚP DANH TÍNH "

    console.print(Panel(Text(badge_text, justify="center"), style=badge_style))

    res_table = Table(title="CHI TIẾT ĐỘ KHỚP THÀNH PHẦN", border_style="cyan")
    res_table.add_column("Chỉ Số", style="bold white")
    res_table.add_column("Kết Quả", justify="right")

    res_table.add_row("Điểm Tin Cậy Tổng Hợp (Trust Score)", f"{res['trust_score'] * 100:.2f}% (Ngưỡng: 72.00%)")
    res_table.add_row("Độ tương đồng Vector Cosine (55%)", f"{res['vec_sim'] * 100:.2f}%")
    res_table.add_row("Độ khớp Trí nhớ Gia đình (30%)", f"{res['fam_sim'] * 100:.2f}%")
    res_table.add_row("Độ khớp Văn phong & Ngữ nghĩa (15%)", f"{res['word_sim'] * 100:.2f}%")
    res_table.add_row("Thế hệ hiện tại", f"Gen #{res['generation']}")
    console.print(res_table)


# =========================================================================
# LỆNH: EVOLVE (TIẾN HÓA EMA)
# =========================================================================

def cmd_evolve(args: argparse.Namespace) -> None:
    engine = get_engine()
    data: dict[str, Any] = {}
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "google": args.google or "",
            "apple": args.apple or "",
            "facebook": args.facebook or "",
            "dob": args.dob or "",
            "family": args.family or "",
            "traits": [t.strip() for t in args.traits.split(",") if t.strip()] if args.traits else [],
            "password": args.password or "",
            "answer": args.answer or ""
        }

    res = engine.verify_and_evolve(data)
    if not res:
        err_console.print("[red]❌ Két sắt chưa được khởi tạo.[/red]")
        sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    print_banner()
    if res["is_owner"]:
        console.print(f"[bold green]✨ TIẾN HÓA THÀNH CÔNG![/bold green] Hồ sơ của [bold cyan]{res['owner_name']}[/bold cyan] đã tự động thích nghi lên [bold yellow]Gen #{res['generation']}[/bold yellow]!")
        console.print(f"• Điểm tin cậy: [green]{res['trust_score'] * 100:.2f}%[/green]")
    else:
        console.print(f"[bold red]⛔ TIẾN HÓA THẤT BẠI![/bold red] Điểm tin cậy [red]{res['trust_score'] * 100:.2f}%[/red] chưa đạt ngưỡng (72.00%).")


# =========================================================================
# LỆNH: INIT / REGISTER (KHỞI TẠO HỒ SƠ)
# =========================================================================

def cmd_register(args: argparse.Namespace) -> None:
    engine = get_engine()
    data: dict[str, Any] = {}
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "owner_name": args.name or "HÀ HỮU HƯNG (1985)",
            "google": args.google or "",
            "apple": args.apple or "",
            "facebook": args.facebook or "",
            "dob": args.dob or "",
            "family": args.family or "",
            "traits": [t.strip() for t in args.traits.split(",") if t.strip()] if args.traits else [],
            "password": args.password or "",
            "answer": args.answer or ""
        }

    try:
        profile = engine.register_owner(data, force=args.force)
        if args.json:
            print(json.dumps(profile, indent=2, ensure_ascii=False))
            return
        print_banner()
        console.print(f"[bold green]🎉 KHỞI TẠO THÀNH CÔNG![/bold green] Hạt giống số của [bold cyan]{profile['owner_name']}[/bold cyan] đã được niêm phong vào két sắt (Gen #1).")
    except Exception as e:
        err_console.print(f"[bold red]❌ Lỗi khởi tạo:[/bold red] {e}")
        sys.exit(1)


# =========================================================================
# LỆNH: LEGACY (QUẢN TRỊ DI SẢN SỐ)
# =========================================================================

def cmd_legacy(args: argparse.Namespace) -> None:
    engine = get_engine()
    sub = args.legacy_action

    if sub == "status":
        status = engine.check_inactivity_status(simulated_days_offline=args.simulate_days)
        if not status:
            err_console.print("[yellow]Chưa thiết lập di sản số.[/yellow]")
            return
        if args.json:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print_banner()
            console.print(f"• Người thừa kế: [bold cyan]{status.get('heir_name_display')}[/bold cyan]")
            console.print(f"• Thời gian vắng mặt: [yellow]{status.get('elapsed_days'):.1f} / {status.get('threshold_days')} ngày[/yellow]")
            console.print(f"• Khả năng mở khóa: [{'bold green]ĐÃ ĐỦ ĐIỀU KIỆN (>= 730 ngày)[/bold green]' if status.get('is_unlockable') else '[bold blue]ĐANG KHÓA AN TOÀN[/bold blue]'}")

    elif sub == "claim":
        res = engine.verify_kin_with_biometrics(
            kin_name=args.kin_name or "",
            kin_email=args.kin_email or "",
            owner_dob=args.owner_dob or "",
            other_family_members=args.family or "",
            family_secret_input=args.secret or "",
            simulated_days_offline=args.simulate_days
        )
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
            return
        print_banner()
        if res.get("is_unlocked"):
            console.print(f"[bold green]🔓 DI SẢN SỐ ĐÃ ĐƯỢC MỞ KHÓA CHO:[/bold green] [bold cyan]{args.kin_name}[/bold cyan]")
            console.print(f"• Thông điệp trao truyền: [italic]{res.get('message')}[/italic]")
            console.print("• Danh mục tài sản số bàn giao:")
            for asset in res.get("assets", []):
                console.print(f"  - [yellow]{asset}[/yellow]")
        else:
            console.print(f"[bold red]⛔ KHÔNG THỂ MỞ KHÓA:[/bold red] Độ khớp tri thức: {res.get('knowledge_score', 0)*100:.1f}%, Thời gian offline: {res.get('elapsed_days', 0):.1f}/{res.get('threshold_days', 730)} ngày.")


# =========================================================================
# LỆNH: PERSONA (XUẤT SYSTEM PROMPT ĐỒNG HÀNH)
# =========================================================================

def cmd_persona(args: argparse.Namespace) -> None:
    engine = get_engine()
    prompt = engine.generate_persona_prompt()
    if args.json:
        print(json.dumps({"persona_prompt": prompt}, indent=2, ensure_ascii=False))
    else:
        print(prompt)


# =========================================================================
# LỆNH: MCP & SERVE (KHỞI CHẠY DỊCH VỤ)
# =========================================================================

def cmd_mcp(args: argparse.Namespace) -> None:
    """Khởi chạy MCP Server."""
    from soul_mcp import run_server
    transport = "sse" if args.sse else "stdio"
    run_server(transport=transport, host=args.host, port=args.port)


def cmd_serve(args: argparse.Namespace) -> None:
    """Khởi chạy REST API FastAPI Server."""
    import uvicorn
    console.print(f"[bold green]🚀 Đang khởi động Evolving Soul AI REST Gateway tại http://{args.host}:{args.port}...[/bold green]")
    console.print(f"📖 Tài liệu tương tác Swagger UI: [cyan]http://{args.host}:{args.port}/docs[/cyan]")
    uvicorn.run("soul_api:app", host=args.host, port=args.port, reload=args.reload)


# =========================================================================
# MAIN ARGPARSE DISPATCHER
# =========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="soul",
        description="Evolving Soul AI — Bộ công cụ dòng lệnh quản lý linh hồn số, MCP và API Gateway"
    )
    parser.add_argument("--json", action="store_true", help="Xuất kết quả dưới định dạng JSON máy đọc được")
    subparsers = parser.add_subparsers(dest="subcommand", help="Lệnh chức năng")

    # status
    p_status = subparsers.add_parser("status", help="Xem trạng thái hồ sơ, thế hệ và 5 trụ cột radar")
    p_status.set_defaults(func=cmd_status)

    # verify
    p_verify = subparsers.add_parser("verify", help="Xác minh danh tính chủ nhân phi sinh trắc học")
    p_verify.add_argument("--file", help="Đường dẫn file JSON chứa thông số xác thực")
    p_verify.add_argument("--google", help="Google OAuth ID/Email")
    p_verify.add_argument("--apple", help="Apple ID")
    p_verify.add_argument("--facebook", help="Facebook ID")
    p_verify.add_argument("--dob", help="Ngày sinh (YYYY-MM-DD)")
    p_verify.add_argument("--family", help="Danh sách tên người thân")
    p_verify.add_argument("--traits", help="Nét cá tính, phân tách bởi dấu phẩy")
    p_verify.add_argument("--password", help="Mẫu mật khẩu (để phân tích thói quen cấu trúc)")
    p_verify.add_argument("--answer", help="Câu trả lời tự do (để phân tích văn phong Stylometry)")
    p_verify.set_defaults(func=cmd_verify)

    # evolve
    p_evolve = subparsers.add_parser("evolve", help="Kích hoạt chu kỳ học liên tục EMA tiến hóa lên Gen #N+1")
    p_evolve.add_argument("--file", help="Đường dẫn file JSON chứa thông số tiến hóa")
    p_evolve.add_argument("--google", help="Google OAuth ID/Email")
    p_evolve.add_argument("--apple", help="Apple ID")
    p_evolve.add_argument("--facebook", help="Facebook ID")
    p_evolve.add_argument("--dob", help="Ngày sinh (YYYY-MM-DD)")
    p_evolve.add_argument("--family", help="Danh sách tên người thân")
    p_evolve.add_argument("--traits", help="Nét cá tính")
    p_evolve.add_argument("--password", help="Mẫu mật khẩu")
    p_evolve.add_argument("--answer", help="Câu trả lời tự do")
    p_evolve.set_defaults(func=cmd_evolve)

    # init / register
    p_reg = subparsers.add_parser("init", help="Khởi tạo Hạt giống Số (Gen #1) trong két sắt")
    p_reg.add_argument("--name", default="HÀ HỮU HƯNG (1985)", help="Tên chủ nhân")
    p_reg.add_argument("--file", help="Đường dẫn file JSON khởi tạo")
    p_reg.add_argument("--google", help="Google OAuth ID/Email")
    p_reg.add_argument("--apple", help="Apple ID")
    p_reg.add_argument("--facebook", help="Facebook ID")
    p_reg.add_argument("--dob", help="Ngày sinh (YYYY-MM-DD)")
    p_reg.add_argument("--family", help="Tên các thành viên gia đình")
    p_reg.add_argument("--traits", help="Nét cá tính")
    p_reg.add_argument("--password", help="Mẫu mật khẩu")
    p_reg.add_argument("--answer", help="Câu trả lời tự do")
    p_reg.add_argument("--force", action="store_true", help="Ghi đè hồ sơ nếu đã tồn tại")
    p_reg.set_defaults(func=cmd_register)

    # legacy
    p_leg = subparsers.add_parser("legacy", help="Quản trị giao thức Di sản Số (Dead Man's Switch 2 năm)")
    sub_leg = p_leg.add_subparsers(dest="legacy_action", required=True)

    p_leg_stat = sub_leg.add_parser("status", help="Xem tiến độ đồng hồ đếm ngược 730 ngày")
    p_leg_stat.add_argument("--simulate-days", type=float, default=0.0, help="Số ngày mô phỏng offline (Demo mode)")

    p_leg_claim = sub_leg.add_parser("claim", help="Người thừa kế mở khóa di sản số")
    p_leg_claim.add_argument("--kin-name", required=True, help="Tên người thừa kế")
    p_leg_claim.add_argument("--kin-email", required=True, help="Email người thừa kế")
    p_leg_claim.add_argument("--owner-dob", required=True, help="Ngày sinh của chủ nhân")
    p_leg_claim.add_argument("--family", required=True, help="Mạng lưới người thân")
    p_leg_claim.add_argument("--secret", required=True, help="Mật ước / tín vật gia đình")
    p_leg_claim.add_argument("--simulate-days", type=float, default=0.0, help="Số ngày mô phỏng offline")
    p_leg.set_defaults(func=cmd_legacy)

    # persona
    p_persona = subparsers.add_parser("persona", help="Xuất Persona System Prompt để AI Agent nhập vai")
    p_persona.set_defaults(func=cmd_persona)

    # mcp
    p_mcp = subparsers.add_parser("mcp", help="Khởi động Model Context Protocol (MCP) Server")
    p_mcp.add_argument("--sse", action="store_true", help="Chạy ở chế độ SSE thay vì stdio")
    p_mcp.add_argument("--host", default="127.0.0.1", help="Host lắng nghe SSE")
    p_mcp.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe SSE")
    p_mcp.set_defaults(func=cmd_mcp)

    # serve
    p_serve = subparsers.add_parser("serve", help="Khởi động REST API Gateway (FastAPI + Swagger UI)")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host lắng nghe")
    p_serve.add_argument("--port", type=int, default=8080, help="Cổng lắng nghe")
    p_serve.add_argument("--reload", action="store_true", help="Tự động reload khi sửa code")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        print_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
