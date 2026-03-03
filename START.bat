@echo off
REM WildTrackAI Startup Script for Windows
REM This script helps you quickly start the WildTrackAI system

setlocal enabledelayedexpansion
title WildTrackAI System Launcher

cls
color 0A

echo.
echo ════════════════════════════════════════════════════════════════════
echo  🐾 WildTrackAI - Animal Identification System 🐾
echo ════════════════════════════════════════════════════════════════════
echo.
echo Choose an option:
echo.
echo 1. Start Backend Server (http://localhost:8000)
echo 2. Start Frontend Application (http://localhost:3000)
echo 3. Train the Model (First time only)
echo 4. Re-download Dataset
echo 5. View API Documentation (requires backend running)
echo 6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto backend
if "%choice%"=="2" goto frontend
if "%choice%"=="3" goto train
if "%choice%"=="4" goto dataset
if "%choice%"=="5" goto docs
if "%choice%"=="6" goto end
echo Invalid choice. Please try again.
goto menu

:backend
cls
echo.
echo Starting Backend Server...
echo.
cd /d "d:\Wild Track AI\backend"
call venv\Scripts\activate.bat
echo.
echo FastAPI Server starting at http://localhost:8000
echo API Documentation: http://localhost:8000/docs
echo.
python main.py
pause
goto menu

:frontend
cls
echo.
echo Starting Frontend Application...
echo.
cd /d "d:\Wild Track AI\frontend"
set PATH=C:\Program Files\nodejs;%PATH%
echo.
echo React app starting at http://localhost:3000
echo.
call npm run dev
pause
goto menu

:train
cls
echo.
echo Training CNN Model...
echo.
echo This will take approximately 30-50 minutes on CPU.
echo For faster training, use a GPU.
echo.
cd /d "d:\Wild Track AI\backend"
call venv\Scripts\activate.bat
cd training
echo.
python train.py
pause
goto menu

:dataset
cls
echo.
echo Re-downloading Dataset...
echo.
cd /d "d:\Wild Track AI\backend"
call venv\Scripts\activate.bat
python scrape_dataset.py
pause
goto menu

:docs
cls
echo.
echo Opening API Documentation...
echo.
echo If backend is running, the documentation should open in your browser.
echo.
start http://localhost:8000/docs
timeout /t 2 /nobreak
goto menu

:end
cls
echo.
echo Thank you for using WildTrackAI!
echo.
echo 📚 Documentation:
echo    - QUICKSTART.md: Quick start guide
echo    - README.md: Complete documentation
echo    - PROJECT_SUMMARY.md: Project overview
echo.
echo Visit: https://github.com/yourname/WildTrackAI
echo.
pause
exit
