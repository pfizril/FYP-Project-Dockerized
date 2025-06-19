@echo off
echo PostgreSQL Setup Script for Health Monitoring System
echo ===================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python is installed. Checking PostgreSQL dependencies...

REM Install PostgreSQL dependencies
echo Installing PostgreSQL dependencies...
pip install -r postgresql_requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install PostgreSQL dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.
echo Starting PostgreSQL setup...
echo.

REM Run the PostgreSQL setup script
python postgresql_setup.py

if errorlevel 1 (
    echo.
    echo ERROR: PostgreSQL setup failed
    echo Please check the error messages above and try again
    pause
    exit /b 1
)

echo.
echo PostgreSQL setup completed successfully!
echo You can now start your health monitoring application.
echo.
pause 