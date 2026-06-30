@echo off
chcp 65001 >nul
set HF_HUB_DISABLE_SYMLINKS=1
echo ============================================================
echo OmniVoice Studio - Starting
echo ============================================================

cd /d "%~dp0"

echo.
echo [1] Creating required directories...
if not exist "media_uploads" mkdir media_uploads
if not exist "output_videos" mkdir output_videos
if not exist "temp_debug" mkdir temp_debug
if not exist "input" mkdir input
if not exist "output" mkdir output

echo.
echo [2] Starting Backend (port 8000)...
start "OmniVoice Backend" cmd /k "python web_api.py"

timeout /t 3 /nobreak >nul

echo.
echo [3] Starting Frontend (port 5173)...
start "OmniVoice Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================================
echo Done! Open browser at:
echo   http://localhost:5173
echo ============================================================
echo.
pause

start http://localhost:5173