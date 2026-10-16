"""
Giao Diện Dòng Lệnh Chuyên Nghiệp (Rich CLI) — Evolving Soul AI V3
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Bảng biểu màu sắc, thanh radar 5 trụ cột, cờ --json cho tự động hóa và lệnh khởi chạy MCP Server & REST API.
Passphrase két sắt lấy từ EVOLVING_SOUL_PASSPHRASE; nếu chưa đặt và đang ở terminal tương tác thì hỏi bằng getpass.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any, Callable

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from evolving_soul import EvolvingSoulError, LockedOutError, service
from evolving_soul.config import ENV_PASSPHRASE

console = Console()
err_console = Console(stderr=True)


def print_banner() -> None:
    banner = Text()
    banner.append("🛡️  EVOLVING SOUL AI V3 — HỆ THỐNG ĐỊNH DANH SỐ & TIẾN HÓA\n", style="bold cyan")
    banner.append("Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X\n", style="bold green")
    banner.append("Zero-Knowledge • 5 Trụ Cột Radar • Dead Man's Switch 730 ngày", style="dim")
    console.print(Panel(banner, border_style="bright_blue", expand=False))


def ensure_passphrase(confirm: bool = False) -> None:
    """Hỏi passphrase khi chưa có trong môi trường (chỉ ở terminal tương tác)."""
    if os.environ.get(ENV_PASSPHRASE):
        return
    # Windows coi thiết bị NUL là "tty" -> kiểm tra thêm stderr để không treo khi chạy tự động
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise EvolvingSoulError(f"Chưa đặt {ENV_PASSPHRASE} và không ở terminal tương tác.")
    passphrase = getpass.getpass("🔑 Passphrase két sắt: ")
    if confirm and getpass.getpass("🔑 Nhập lại passphrase: ") != passphrase:
        raise EvolvingSoulError("Hai lần nhập passphrase không khớp.")
    os.environ[ENV_PASSPHRASE] = passphrase


def run(action: Callable[[], Any]) -> Any:
    """Chạy thao tác, in lỗi thân thiện và thoát mã 1 thay vì traceback."""
    try:
        return action()
    except LockedOutError as exc:
        err_console.print(f"[bold red]⏳ {exc}[/bold red]")
    except (EvolvingSoulError, PermissionError, ValueError, OSError) as exc:
        err_console.print(f"[bold red]❌ {exc}[/bold red]")
    sys.exit(1)


def emit_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def identity_from_args(args: argparse.Namespace, owner_name: str | None = None) -> dict:
    if getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as f:
            data = json.load(f)
        if owner_name is not None:
            data.setdefault("owner_name", owner_name)
        return data
    return service.identity(
        google=args.google, apple=args.apple, facebook=args.facebook, dob=args.dob, family=args.family,
        traits=[t.strip() for t in args.traits.split(",") if t.strip()] if args.traits else [],
        password=args.password, answer=args.answer, owner_name=owner_name,
    )


def pct_bar(value: float | None) -> str:
    if value is None:
        return "[dim]— chưa liên kết[/dim]"
    pct = max(0.0, min(float(value), 1.0)) * 100
    color = "green" if pct >= 70 else "yellow" if pct >= 40 else "red"
    filled = int(pct / 5)
    return f"[{color}]{'█' * filled}{'░' * (20 - filled)}[/{color}] {pct:5.1f}%"


# =========================================================================
# LỆNH: STATUS
# =========================================================================

def cmd_status(args: argparse.Namespace) -> None:
    run(ensure_passphrase)
    summary = run(lambda: service.profile_summary(service.open_engine()))
    if args.json:
        emit_json(summary)
        return
    print_banner()
    if not summary["is_initialized"]:
        err_console.print("[yellow]⚠️  Két sắt chưa có hồ sơ Chủ nhân.[/yellow] Dùng [bold cyan]soul init[/bold cyan] để khởi tạo.")
        return

    info = Table(title="📋 THÔNG TIN CHỦ NHÂN & THẾ HỆ", border_style="cyan", show_header=False)
    info.add_column("Thuộc tính", style="bold white", width=24)
    info.add_column("Giá trị", style="green")
    info.add_row("Chủ nhân", str(summary["owner_name"]))
    info.add_row("Soul ID", str(summary["soul_id"] or "Đang chờ hoàn tất nâng cấp V2"))
    info.add_row("Thế hệ tiến hóa", f"Gen #{summary['generation']}")
    info.add_row("Khởi tạo", str(summary["created_at"]))
    info.add_row("Cập nhật gần nhất", str(summary["last_updated"]))
    info.add_row("Nét cá tính", ", ".join(summary["traits"]) or "Chưa khai báo")
    console.print(info)

    radar = Table(title="📊 5 TRỤ CỘT ĐẶC TRƯNG (CHỮ KÝ GỐC EMA)", border_style="bright_blue")
    radar.add_column("Trụ cột", style="bold white", width=32)
    radar.add_column("Điểm", width=34)
    for pillar, value in summary["radar_metrics"].items():
        radar.add_row(pillar, pct_bar(value))
    console.print(radar)

    legacy = summary["legacy_status"]
    if legacy:
        state = "[red]CỔNG TIẾP QUẢN ĐANG MỞ[/red]" if legacy["is_unlockable"] else (
            "[yellow]CẢNH BÁO — sắp chạm ngưỡng[/yellow]" if legacy["warning"] else "[green]ĐANG BẢO VỆ CHỦ NHÂN[/green]")
        console.print(Panel(
            f"• Người thừa kế: {legacy['heir_name_display']}\n"
            f"• Vắng mặt: {legacy['elapsed_days']:.1f} / {legacy['threshold_days']} ngày\n"
            f"• Trạng thái: {state}\n"
            f"• Lớp sinh trắc: {legacy['biometric_method'] or 'không có'}",
            title="⏳ DI SẢN SỐ (DEAD MAN'S SWITCH)", border_style="gold1"))


# =========================================================================
# LỆNH: VERIFY / EVOLVE
# =========================================================================

def cmd_verify(args: argparse.Namespace) -> None:
    run(ensure_passphrase)
    data = identity_from_args(args)
    result = run(lambda: service.verify_summary(service.open_engine().verify_owner(data)))
    if args.json:
        emit_json(result)
        return
    print_banner()
    ok = result["is_owner"]
    console.print(Panel(Text(" ✅ XÁC MINH THÀNH CÔNG — CHÍNH CHỦ " if ok else " ❌ TỪ CHỐI — KHÔNG KHỚP DANH TÍNH ",
                             justify="center"), style="bold white on green" if ok else "bold white on red"))
    table = Table(title="CHI TIẾT 5 TRỤ CỘT", border_style="cyan")
    table.add_column("Chỉ số", style="bold white", width=36)
    table.add_column("Kết quả", width=34)
    table.add_row("Điểm tin cậy tổng hợp", f"{result['trust_score'] * 100:.2f}% (ngưỡng {result['threshold'] * 100:.0f}%)")
    table.add_row("Cổng tri thức (ngày sinh / người thân)", "[green]đạt[/green]" if result["gate_passed"] else "[red]chưa đạt[/red]")
    for pillar, value in result["pillars"].items():
        table.add_row(pillar, pct_bar(value))
    table.add_row("Thế hệ hiện tại", f"Gen #{result['current_generation']}")
    console.print(table)


def cmd_evolve(args: argparse.Namespace) -> None:
    run(ensure_passphrase)
    data = identity_from_args(args)
    result = run(lambda: service.verify_summary(service.open_engine().verify_owner(data)))
    if args.json:
        emit_json(result)
        return
    print_banner()
    if result["is_owner"]:
        console.print(f"[bold green]✨ TIẾN HÓA THÀNH CÔNG![/bold green] [bold cyan]{result['owner_name']}[/bold cyan] "
                      f"→ [bold yellow]Gen #{result['current_generation']}[/bold yellow] "
                      f"(tin cậy {result['trust_score'] * 100:.2f}%)")
    else:
        console.print(f"[bold red]⛔ KHÔNG TIẾN HÓA:[/bold red] điểm tin cậy {result['trust_score'] * 100:.2f}% "
                      f"< ngưỡng {result['threshold'] * 100:.0f}%.")


# =========================================================================
# LỆNH: INIT
# =========================================================================

def cmd_register(args: argparse.Namespace) -> None:
    run(lambda: ensure_passphrase(confirm=True))
    data = identity_from_args(args, owner_name=args.name)
    current = None
    if args.force:
        if not args.current_file:
            err_console.print("[bold red]❌ --force cần --current-file (định danh hiện tại để xác minh).[/bold red]")
            sys.exit(1)
        with open(args.current_file, encoding="utf-8") as f:
            current = json.load(f)
    profile = run(lambda: service.register(service.open_or_create_engine(), data, force=args.force, current_identity=current))
    if args.json:
        emit_json({"status": "REGISTERED", "owner_name": profile["owner_name"], "generation": profile["generation"],
                   "created_at": profile["created_at"], "radar_baseline": profile["radar_baseline"]})
        return
    print_banner()
    console.print(f"[bold green]🎉 KHỞI TẠO THÀNH CÔNG![/bold green] Hạt giống số của [bold cyan]{profile['owner_name']}"
                  "[/bold cyan] đã được niêm phong vào két sắt (Gen #1).")


# =========================================================================
# LỆNH: LEGACY
# =========================================================================

def cmd_legacy(args: argparse.Namespace) -> None:
    if args.legacy_action == "status":
        run(ensure_passphrase)

        def status():
            engine = service.open_engine()
            service.apply_demo_days(engine, args.simulate_days)
            return engine.legacy_status()

        legacy = run(status)
        if args.json:
            emit_json(legacy or {"status": "NOT_CONFIGURED"})
            return
        print_banner()
        if not legacy:
            err_console.print("[yellow]Chưa niêm phong Di sản Số.[/yellow]")
            return
        console.print(f"• Người thừa kế: [bold cyan]{legacy['heir_name_display']}[/bold cyan]")
        console.print(f"• Vắng mặt: [yellow]{legacy['elapsed_days']:.1f} / {legacy['threshold_days']} ngày[/yellow]")
        console.print("• Cổng tiếp quản: " + ("[bold green]ĐANG MỞ[/bold green]" if legacy["is_unlockable"]
                                            else "[bold blue]ĐANG KHÓA AN TOÀN[/bold blue]"))

    elif args.legacy_action == "seal":
        run(ensure_passphrase)
        with open(args.owner_file, encoding="utf-8") as f:
            owner_identity = json.load(f)
        assets = [line.strip() for line in args.assets.split(";") if line.strip()]
        legacy = run(lambda: service.seal_legacy(
            service.open_engine(), owner_identity, heir_name=args.heir_name, heir_email=args.heir_email,
            family_secret=args.secret, assets=assets, message=args.message or "", inactivity_days=args.days,
        ))
        if args.json:
            emit_json({"status": "CONFIGURED", **legacy})
        else:
            print_banner()
            console.print(f"[bold green]🔒 Đã niêm phong Di sản Số[/bold green] cho [cyan]{legacy['heir_name_display']}[/cyan] "
                          f"({legacy['asset_count']} tài sản, ngưỡng {legacy['threshold_days']} ngày).")

    elif args.legacy_action == "claim":
        def claim():
            engine = service.open_engine(unlock=False)
            service.apply_demo_days(engine, args.simulate_days)
            return service.claim_summary(engine.claim_legacy(
                kin_name=args.kin_name, kin_email=args.kin_email, owner_dob=args.owner_dob,
                family_members=args.family, family_secret=args.secret,
            ))

        result = run(claim)
        if args.json:
            emit_json(result)
            return
        print_banner()
        if result["is_unlocked"]:
            console.print(f"[bold green]🔓 DI SẢN SỐ ĐÃ ĐƯỢC MỞ KHÓA CHO:[/bold green] [bold cyan]{args.kin_name}[/bold cyan]")
            console.print(f"• Lời nhắn: [italic]{result['legacy_message']}[/italic]")
            for asset in result["assets_unlocked"]:
                console.print(f"  - [yellow]{asset}[/yellow]")
        else:
            console.print(f"[bold red]⛔ CHƯA MỞ KHÓA:[/bold red] tri thức {result['knowledge_score'] * 100:.1f}%, "
                          f"vắng mặt {result['elapsed_days'] or 0:.1f}/{result['threshold_days'] or 730} ngày. {result['reason']}")


# =========================================================================
# LỆNH: PERSONA / MCP / SERVE
# =========================================================================

def cmd_persona(args: argparse.Namespace) -> None:
    run(ensure_passphrase)
    prompt = run(lambda: service.persona_prompt(service.open_engine()))
    if args.json:
        emit_json({"persona_prompt": prompt})
    else:
        print(prompt)


def cmd_mcp(args: argparse.Namespace) -> None:
    from soul_mcp import run_server
    run_server(transport="sse" if args.sse else "stdio", host=args.host, port=args.port)


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn
    console.print(f"[bold green]🚀 Evolving Soul AI REST Gateway tại http://{args.host}:{args.port}[/bold green]")
    console.print(f"📖 Swagger UI: [cyan]http://{args.host}:{args.port}/docs[/cyan]")
    uvicorn.run("soul_api:app", host=args.host, port=args.port, reload=args.reload)


# =========================================================================
# MAIN
# =========================================================================

def _identity_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--file", help="File JSON chứa định danh (google/apple/facebook/dob/family/traits/password/answer)")
    p.add_argument("--google", help="Google OAuth ID/Email")
    p.add_argument("--apple", help="Apple ID")
    p.add_argument("--facebook", help="Facebook ID")
    p.add_argument("--dob", help="Ngày sinh (YYYY-MM-DD)")
    p.add_argument("--family", help="Danh sách người thân, phân tách bởi dấu phẩy")
    p.add_argument("--traits", help="Nét cá tính, phân tách bởi dấu phẩy")
    p.add_argument("--password", help="Mẫu mật khẩu (chỉ học cấu trúc)")
    p.add_argument("--answer", help="Câu trả lời mở (phân tích văn phong)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="soul", description="Evolving Soul AI V3 — CLI quản lý linh hồn số, MCP và API Gateway")
    parser.add_argument("--json", action="store_true", help="Xuất kết quả JSON")
    sub = parser.add_subparsers(dest="subcommand")

    sub.add_parser("status", help="Hồ sơ, thế hệ, 5 trụ cột và di sản").set_defaults(func=cmd_status)

    p_verify = sub.add_parser("verify", help="Xác minh Chủ nhân (tiến hóa nếu đạt)")
    _identity_args(p_verify)
    p_verify.set_defaults(func=cmd_verify)

    p_evolve = sub.add_parser("evolve", help="Chu kỳ học liên tục EMA")
    _identity_args(p_evolve)
    p_evolve.set_defaults(func=cmd_evolve)

    p_init = sub.add_parser("init", help="Tạo két (nếu chưa có) và khởi tạo Hạt giống Số Gen #1")
    p_init.add_argument("--name", default="HÀ HỮU HƯNG (1985)", help="Tên Chủ nhân")
    _identity_args(p_init)
    p_init.add_argument("--force", action="store_true", help="Ghi đè hồ sơ đã có")
    p_init.add_argument("--current-file", help="File JSON định danh hiện tại (bắt buộc khi --force)")
    p_init.set_defaults(func=cmd_register)

    p_leg = sub.add_parser("legacy", help="Di sản Số (Dead Man's Switch)")
    leg = p_leg.add_subparsers(dest="legacy_action", required=True)
    p_ls = leg.add_parser("status", help="Đồng hồ đếm ngược")
    p_ls.add_argument("--simulate-days", type=float, default=0.0, help="Số ngày offline mô phỏng (chỉ chế độ demo)")
    p_seal = leg.add_parser("seal", help="Niêm phong di sản (xác minh Chủ nhân trong cùng lệnh)")
    p_seal.add_argument("--owner-file", required=True, help="File JSON định danh Chủ nhân để xác minh")
    p_seal.add_argument("--heir-name", required=True)
    p_seal.add_argument("--heir-email", required=True)
    p_seal.add_argument("--secret", required=True, help="Mật ước gia đình (≥ 10 ký tự)")
    p_seal.add_argument("--assets", required=True, help="Danh mục tài sản, phân tách bởi dấu chấm phẩy")
    p_seal.add_argument("--message", help="Lời nhắn cho người thừa kế")
    p_seal.add_argument("--days", type=int, default=730, help="Ngưỡng vắng mặt (ngày)")
    p_claim = leg.add_parser("claim", help="Người thừa kế mở khóa di sản (không cần passphrase)")
    p_claim.add_argument("--kin-name", required=True)
    p_claim.add_argument("--kin-email", required=True)
    p_claim.add_argument("--owner-dob", required=True)
    p_claim.add_argument("--family", required=True)
    p_claim.add_argument("--secret", required=True, help="Mật ước gia đình")
    p_claim.add_argument("--simulate-days", type=float, default=0.0, help="Số ngày offline mô phỏng (chỉ chế độ demo)")
    p_leg.set_defaults(func=cmd_legacy)

    sub.add_parser("persona", help="Xuất Persona System Prompt").set_defaults(func=cmd_persona)

    p_mcp = sub.add_parser("mcp", help="Khởi động MCP Server (Python ≥ 3.10)")
    p_mcp.add_argument("--sse", action="store_true", help="Chạy SSE thay vì stdio")
    p_mcp.add_argument("--host", default="127.0.0.1")
    p_mcp.add_argument("--port", type=int, default=8000)
    p_mcp.set_defaults(func=cmd_mcp)

    p_serve = sub.add_parser("serve", help="Khởi động REST API Gateway (FastAPI + Swagger UI)")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8080)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        print_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
