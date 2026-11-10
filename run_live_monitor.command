#!/bin/bash
cd "$(dirname "$0")"
echo "Starting BPL Dual-Board Ground Station..."
/Users/thoward/Documents/AIAA/venv/bin/python ground_station.py
read -p "Press Enter to close..."
