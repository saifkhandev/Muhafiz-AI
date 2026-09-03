@echo off
title Muhafiz AI - Launcher
echo ============================================
echo   Muhafiz AI - starting both servers
echo ============================================
echo.

echo [1/2] Starting backend (loads model + Whisper, needs ~60 seconds)...
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1
start "Muhafiz Backend :8000" /D "%~dp0scam_detection" cmd /k ""C:\Users\Hp\AppData\Local\Python\bin\python3.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000"

timeout /t 5 /nobreak >nul

echo [2/2] Starting frontend...
start "Muhafiz Frontend :3000" /D "%~dp0scam_detection\web" cmd /k "npm run dev"

echo Waiting for servers to boot, then opening your browser...
timeout /t 18 /nobreak >nul
start "" http://localhost:3000

echo.
echo If the page shows an error at first, wait 30 seconds and refresh
echo (the backend needs about 60 seconds on a cold start).
echo.
echo To STOP the website: close the two server windows.
echo.
pause
