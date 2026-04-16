@echo off
chcp 65001 >nul
echo ============================================================
echo OmniVoice Studio - Starting
echo ============================================================

cd /d "%~dp0"

echo.
echo [1] Starting Backend (port 8000)...
start "OmniVoice Backend" cmd /k "python web_api.py"

timeout /t 3 /nobreak >nul

echo.
echo [2] Starting Frontend (port 5173)...
cd frontend
start "OmniVoice Frontend" cmd /k "npm run dev"

echo.
echo ============================================================
echo Done! Open browser at:
echo   http://localhost:5173
echo ============================================================
echo.
pause

start http://localhost:5173