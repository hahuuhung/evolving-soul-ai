#!/usr/bin/env bash
# Evolving Soul AI — Cross-Platform Launcher for Linux & macOS
# Author: Ha Huu Hung (1985) — 8X Generation AI Engineer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"
export PYTHONIOENCODING="utf-8"

# Detect Python 3
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "Error: Python 3.11+ is required but neither 'python3' nor 'python' was found in PATH." >&2
    exit 1
fi

exec "$PY_BIN" -m evolving_soul.cli "$@"
