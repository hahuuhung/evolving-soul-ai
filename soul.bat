@echo off
REM Evolving Soul AI — Windows Command Launcher
REM Author: Ha Huu Hung (1985) — 8X Generation AI Engineer

chcp 65001 > nul
set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"
set "PYTHONIOENCODING=utf-8"

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.11+.
    exit /b 1
)

python -m evolving_soul.cli %*
