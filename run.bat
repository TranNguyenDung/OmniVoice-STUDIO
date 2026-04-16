@echo off
chcp 65001 >nul
echo ============================================================
echo OmniVoice Studio - Starting
echo ============================================================

cd /d "%~dp0"

echo.
echo [Check] Verifying Python and Node.js...
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python first.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js first.
    echo Download: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] Node.js found

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install Node.js first.
    pause
    exit /b 1
)
echo [OK] npm found

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