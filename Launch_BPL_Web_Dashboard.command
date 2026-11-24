#!/bin/bash
# ==============================================================================
# 🌸 AIAA BPL AVIONICS & TELEMETRY WEB MISSION CONTROL LAUNCHER 🌸
# Double-click to start live web telemetry ground station for macOS!
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR" || exit 1

echo -ne "\033]0;🌸 AIAA BPL Mission Control Web Dashboard 🌸\007"

# If server is already running, simply bring up the browser window!
if lsof -i :5050 >/dev/null 2>&1; then
    echo -e "\033[38;5;48m[✓] Telemetry server already active on http://localhost:5050\033[0m"
    echo -e "\033[38;5;205m[✓] Popping open dashboard in browser...\033[0m"
    open "http://localhost:5050"
    exit 0
fi

# Locate Python
if [ -f "/Users/thoward/.cache/venvs/AIAA/venv/bin/python" ]; then
    VENV_PY="/Users/thoward/.cache/venvs/AIAA/venv/bin/python"
elif [ -f "/Users/thoward/Documents/AIAA/venv/bin/python" ]; then
    VENV_PY="/Users/thoward/Documents/AIAA/venv/bin/python"
elif [ -f "$DIR/venv/bin/python" ]; then
    VENV_PY="$DIR/venv/bin/python"
else
    VENV_PY="python3"
fi

# Open browser
(sleep 1 && open "http://localhost:5050") &

"$VENV_PY" bpl_web_server.py
