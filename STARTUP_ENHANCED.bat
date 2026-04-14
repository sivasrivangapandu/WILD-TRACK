@echo off
REM Enhanced WildTrackAI Startup Script with Diagnostics
REM This script starts both backend and frontend with better logging
REM Usage: Double-click this file to start the application

setlocal enabledelayedexpansion

title WildTrackAI - Startup Manager
color 0F

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  WILDTRACKAI STARTUP MANAGER                 ║
echo ║                                                              ║
echo ║    🐾 Enhanced startup with diagnostics and monitoring      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Check if in correct directory
if not exist "backend\main.py" (
    echo ✗ Error: backend\main.py not found
    echo   Please run this script from the Wild Track AI root directory
    pause
    exit /b 1
)

echo ✓ Project structure verified
echo.

REM Create a log file
set LOG_FILE=%USERPROFILE%\Desktop\wildtrack_startup_%date:~10,4%-%date:~4,2%-%date:~7,2%_%time:~0,2%-%time:~3,2%-%time:~6,2%.log
echo. > "%LOG_FILE%"
echo WildTrackAI Startup Log >> "%LOG_FILE%"
echo Started: %date% %time% >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo Log file: %LOG_FILE%
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║ Starting Backend Server...                                   ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

REM Start backend in a new window
start "WildTrackAI Backend Server" cmd /k ^
  "cd /d "%CD%\backend" && ^
  call venv\Scripts\activate.bat && ^
  echo. && ^
  echo === Backend Startup Diagnostics === && ^
  python startup_diagnostics.py && ^
  echo. && ^
  echo === Starting FastAPI Server === && ^
  echo   API: http://localhost:8000 && ^
  echo   Docs: http://localhost:8000/docs && ^
  echo   Health: http://localhost:8000/health && ^
  echo. && ^
  echo Please wait 10-15 seconds for the model to load... && ^
  echo. && ^
  python main.py"

echo.
echo ✓ Backend starting in separate window
echo.
echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║ Starting Frontend...                                          ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Start frontend in a new window
start "WildTrackAI Frontend" cmd /k ^
  "cd /d "%CD%\frontend" && ^
  echo === Frontend Startup === && ^
  echo   Dev Server: http://localhost:5173 && ^
  echo   App: http://localhost:3000 && ^
  echo. && ^
  echo Please wait for React to compile... && ^
  echo. && ^
  call npm run dev"

echo.
echo ✓ Frontend starting in separate window
echo.
timeout /t 3 /nobreak

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    STARTUP COMPLETE                          ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo 📋 SERVICES STARTING:
echo   Backend:  http://localhost:8000       (loading model...)
echo   Frontend: http://localhost:5173       (or http://localhost:3000)
echo.
echo ⏱  ESTIMATED TIMES:
echo   Backend ready: 10-15 seconds
echo   Frontend ready: 20-30 seconds  
echo   App fully ready: 30-45 seconds
echo.
echo 📝 TIPS:
echo   - Backend window shows model loading progress
echo   - Frontend window shows React compilation progress
echo   - Close either window to stop that service
echo   - Open http://localhost:3000 in browser when ready
echo.
echo 🔍 TROUBLESHOOTING:
echo   - Port already in use? Change ports or kill existing processes
echo   - Backend not responding? Check backend window for errors
echo   - Models not downloading? Check internet connection
echo   - Log file: %LOG_FILE%
echo.
echo Press any key to close this window (services will keep running)...
pause > nul
