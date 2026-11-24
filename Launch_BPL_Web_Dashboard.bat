@echo off
title 🌸 WMU AIAA BPL Mission Control Ground Station 🌸
color 0D
cls

echo ==============================================================================
echo   🌸 WMU AIAA • BRONCO PROPULSION LABORATORY (BPL) MISSION CONTROL 🌸
echo          Western Michigan University - Avionics & Telemetry Team
echo ==============================================================================
echo.

:: 1. Check Python Installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python 3 was not detected on your system PATH!
    echo [!] Please install Python 3.10+ from python.org and check "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Verify pySerial dependency
echo [*] Checking dependencies...
python -c "import serial" >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing required pySerial package...
    pip install pyserial
)

:: 3. Launch browser after brief 1-second delay
echo [*] Opening telemetry mission control in your default browser...
start "" http://localhost:5050

:: 4. Start BPL Web Telemetry Server
echo [*] Starting high-performance 200 Hz serial DAQ server...
echo.
python bpl_web_server.py

pause
