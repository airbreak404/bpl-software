#!/usr/bin/env bash
# ==============================================================================
# 🌸 WMU AIAA • BRONCO PROPULSION LABORATORY MISSION CONTROL (LINUX) 🌸
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo -e "\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m"
echo -e "\033[1;38;5;205m     ✨ WMU AIAA BPL AVIONICS & TELEMETRY MISSION CONTROL ✨\033[0m"
echo -e "\033[38;5;141m          Western Michigan University • Linux Launcher\033[0m"
echo -e "\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m"

# 1. Check Python 3
if ! command -v python3 &>/dev/null; then
    echo -e "\033[38;5;196m[!] Python 3 is required. Please install python3 (e.g. sudo apt install python3 python3-pip).\033[0m"
    exit 1
fi

# 2. Check pySerial
if ! python3 -c "import serial" &>/dev/null; then
    echo -e "\033[38;5;218m[*] Installing pySerial...\033[0m"
    pip3 install --user pyserial || pip install pyserial
fi

# 3. Open browser
if command -v xdg-open &>/dev/null; then
    (sleep 1 && xdg-open "http://localhost:5050") &
elif command -v google-chrome &>/dev/null; then
    (sleep 1 && google-chrome "http://localhost:5050") &
elif command -v firefox &>/dev/null; then
    (sleep 1 && firefox "http://localhost:5050") &
fi

# 4. Start Server
exec python3 bpl_web_server.py
