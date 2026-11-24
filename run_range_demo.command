#!/bin/bash
# ==============================================================================
# 🌸 AIAA BPL AVIONICS & TELEMETRY LIVE DEMO LAUNCHER 🌸
# Double-click to start the live rocket motor & RF ground station for the team!
# ==============================================================================

cd "/Users/thoward/Repos/bpl-software" || exit 1

# Set Mac terminal window title
echo -ne "\033]0;🌸 AIAA BPL Telemetry & Range Ground Station 🌸\007"

VENV_PY="/Users/thoward/Documents/AIAA/venv/bin/python"
if [ ! -f "$VENV_PY" ]; then
    VENV_PY="/Users/thoward/venv/bin/python"
fi

"$VENV_PY" bpl_live_demo.py

echo ""
echo "Press Enter to exit..."
read -r
