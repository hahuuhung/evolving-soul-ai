"""Model Context Protocol (MCP) Server — Evolving Soul AI.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)

Cung cấp giao diện chuẩn MCP (Model Context Protocol) cho Claude Desktop, Antigravity IDE, Cursor
và các hệ thống AI Agents bên ngoài liên kết, thẩm định danh tính và đồng hành cùng Evolving Soul AI.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure Windows terminal handles UTF-8 safely without charmap crashes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure research/legacy-v2 directory is in sys.path
_LEGACY_DIR = Path(__file__).resolve().parent / "research" / "legacy-v2"
if _LEGACY_DIR.exists() and str(_LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(_LEGACY_DIR))

_import_error = None
try:
    from soul_mcp import mcp, run_server

    def main(argv: list[str] | None = None) -> None:
        import argparse
        parser = argparse.ArgumentParser(description="Evolving Soul AI — MCP Server")
        parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="Phương thức truyền thông MCP (stdio / sse)")
        parser.add_argument("--host", default="127.0.0.1", help="Địa chỉ host khi chạy SSE")
        parser.add_argument("--port", type=int, default=8000, help="Cổng lắng nghe khi chạy SSE")
        args = parser.parse_args(argv)
        run_server(transport=args.transport, host=args.host, port=args.port)

except ImportError as err:
    _import_error = str(err)

    def main(argv: list[str] | None = None) -> None:
        sys.stderr.write(
            f"Error loading soul_mcp: {_import_error}. Please install dependencies: pip install mcp fastapi uvicorn\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
