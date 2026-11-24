#!/bin/bash
# ==============================================================================
# 🌸 AIAA BPL AVIONICS & TELEMETRY WEB MISSION CONTROL LAUNCHER 🌸
# Double-click to start live web telemetry ground station for Olivia & the team!
# ==============================================================================

cd "/Users/thoward/Repos/bpl-software" || exit 1

echo -ne "\033]0;🌸 AIAA BPL Mission Control Web Dashboard 🌸\007"

if [ -f "/Users/thoward/.cache/venvs/AIAA/venv/bin/python" ]; then
    VENV_PY="/Users/thoward/.cache/venvs/AIAA/venv/bin/python"
elif [ -f "/Users/thoward/Documents/AIAA/venv/bin/python" ]; then
    VENV_PY="/Users/thoward/Documents/AIAA/venv/bin/python"
elif [ -f "/Users/thoward/venv/bin/python" ]; then
    VENV_PY="/Users/thoward/venv/bin/python"
else
    VENV_PY="python3"
fi

"$VENV_PY" bpl_web_server.py
