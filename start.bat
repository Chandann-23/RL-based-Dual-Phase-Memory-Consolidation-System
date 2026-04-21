@echo off
title RL Memory System
echo.
echo  Starting RL Memory System...
echo.

:: Start Flask in background
start "Flask Backend" cmd /k "cd /d %~dp0 && set PYTHONPATH=. && python run.py"

:: Wait for Flask to boot
timeout /t 4 /nobreak > nul

:: Open the frontend in browser
start "" "%~dp0frontend\index.html"

echo  App launched! Flask is running in the background.
echo  Close the Flask window to shut down the backend.