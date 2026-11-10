@echo off
setlocal
title BPL Ground Station - Telemetry Monitor
color 0F

echo =================================================================
echo        BPL STATIC TEST STAND - DUAL-BOARD TELEMETRY (WINDOWS)
echo =================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10+ from https://www.python.org/ or the Microsoft Store.
    echo (Make sure to check "Add Python to PATH" during installation)
    echo.
    pause
    exit /b 1
)

:: Check if in virtual environment or if requirements need to be checked
if exist "venv\Scripts\python.exe" (
    echo Using local venv Python environment...
    venv\Scripts\python.exe ground_station.py %*
) else (
    echo Using system Python...
    python -c "import serial" >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo [INFO] Installing required serial package (pyserial)...
        pip install pyserial
    )
    python ground_station.py %*
)

echo.
echo Test session ended.
pause
