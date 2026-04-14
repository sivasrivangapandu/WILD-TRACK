@echo off
REM WildTrack AI - Deployment Wizard Launcher
REM Run this file to start the interactive deployment process

setlocal enabledelayedexpansion

echo.
echo ========================================
echo WildTrack AI - Render Deployment Wizard
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.10+ from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Starting deployment wizard...
echo.

python deployment_wizard.py

if errorlevel 1 (
    echo.
    echo Deployment wizard exited with an error.
    pause
    exit /b 1
) else (
    echo.
    echo Deployment wizard completed successfully!
    pause
    exit /b 0
)
