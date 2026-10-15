#!/usr/bin/env bash
# Evolving Soul AI — 1-Click Control Plane Launcher for Linux & macOS
# Author: Ha Huu Hung (1985) — 8X Generation AI Engineer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VAULT_DIR="${SCRIPT_DIR}/.soul-vault"

echo "================================================================="
echo "   EVOLVING SOUL AI — 1-CLICK DEMO LAUNCHER (LINUX / MACOS)      "
echo "   Author: Ha Huu Hung (1985) — 8X Generation AI Engineer        "
echo "================================================================="

# Run doctor check
"${SCRIPT_DIR}/soul.sh" doctor

# Initialize vault if missing
if [ ! -f "${VAULT_DIR}/vault.json" ]; then
    echo ""
    echo "[INFO] Initializing new local vault at ${VAULT_DIR}..."
    "${SCRIPT_DIR}/soul.sh" --vault "${VAULT_DIR}" init
fi

echo ""
echo "[INFO] Vault status:"
"${SCRIPT_DIR}/soul.sh" --vault "${VAULT_DIR}" status

echo ""
echo "[INFO] Starting Control Plane UI on http://127.0.0.1:8765..."
echo "[INFO] Open your browser and navigate to http://127.0.0.1:8765"
echo "================================================================="

exec "${SCRIPT_DIR}/soul.sh" --vault "${VAULT_DIR}" serve --host 127.0.0.1 --port 8765
