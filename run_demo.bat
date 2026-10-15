@echo off
REM Evolving Soul AI — 1-Click Control Plane Launcher for Windows
REM Author: Ha Huu Hung (1985) — 8X Generation AI Engineer

chcp 65001 > nul
set "SCRIPT_DIR=%~dp0"
set "VAULT_DIR=%SCRIPT_DIR%.soul-vault"

echo =================================================================
echo    EVOLVING SOUL AI — 1-CLICK DEMO LAUNCHER (WINDOWS)
echo    Author: Ha Huu Hung (1985) — 8X Generation AI Engineer
echo =================================================================

REM Run doctor check
call "%SCRIPT_DIR%soul.bat" doctor

REM Initialize vault if missing
if not exist "%VAULT_DIR%\vault.json" (
    echo.
    echo [INFO] Initializing new local vault at %VAULT_DIR%...
    call "%SCRIPT_DIR%soul.bat" --vault "%VAULT_DIR%" init
)

echo.
echo [INFO] Vault status:
call "%SCRIPT_DIR%soul.bat" --vault "%VAULT_DIR%" status

echo.
echo [INFO] Starting Control Plane UI on http://127.0.0.1:8765...
echo [INFO] Open your browser and navigate to http://127.0.0.1:8765
echo =================================================================

call "%SCRIPT_DIR%soul.bat" --vault "%VAULT_DIR%" serve --host 127.0.0.1 --port 8765
