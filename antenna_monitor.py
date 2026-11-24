#!/usr/bin/env python3
"""
==============================================================================
Bronco Propulsion Laboratory (BPL) - Antenna RF Live Monitor
==============================================================================
Connects to the ESP32 receiver board and displays real-time:
  - RSSI in dBm (Signal Strength)
  - Color-coded RF visual signal bar
  - Packet count & dropped packets percentage
  - Min / Average / Max RSSI
==============================================================================
"""

import sys
import os
import time
import glob
import serial
import serial.tools.list_ports

# Color definitions
PINK = "\033[38;5;205m"
CYAN = "\033[38;5;51m"
GREEN = "\033[38;5;48m"
YELLOW = "\033[38;5;220m"
RED = "\033[38;5;196m"
BOLD = "\033[1m"
RESET = "\033[0m"

def find_serial_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if p.vid in [0x1A86, 0x303A, 0x10C4, 0x0403]:
            return p.device
    for p in ports:
        desc = (p.description or "").lower()
        if any(term in desc for term in ["espressif", "ch34", "cp210", "ftdi", "uart", "usbmodem"]):
            return p.device
    mac_ports = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wch*")
    if mac_ports:
        return mac_ports[0]
    return None

def draw_bar(rssi):
    # Scale from -100 dBm (0 bars) to -30 dBm (35 bars)
    clamped = max(-100, min(-30, rssi))
    ratio = (clamped - (-100)) / 70.0
    bar_len = int(ratio * 35)

    if rssi >= -65:
        color = GREEN
        label = "EXCELLENT"
    elif rssi >= -78:
        color = YELLOW
        label = "GOOD"
    elif rssi >= -85:
        color = YELLOW
        label = "FAIR / WEAK"
    else:
        color = RED
        label = "POOR (DROP-OUT)"

    bar = color + "█" * bar_len + "░" * (35 - bar_len) + RESET
    return bar, color, label

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    if not port:
        print(f"{RED}[!] No ESP32 serial port detected.{RESET}")
        print("Please plug in the ESP32 receiver board and re-run.")
        sys.exit(1)

    print(f"\n{PINK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}    📡 BPL ANTENNA RF BENCHMARK — LIVE RSSI MONITOR 📡{RESET}")
    print(f"{PINK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"Connecting to: {CYAN}{port}{RESET} (115200 baud)...")

    try:
        ser = serial.Serial(port, 115200, timeout=1.0)
        ser.dtr = False
        ser.rts = False
    except Exception as e:
        print(f"{RED}[!] Error opening {port}: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[✓] Connected! Listening for RF packets...{RESET}\n")

    rssi_history = []
    total_received = 0
    total_dropped = 0

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("CSV:"):
                # Print non-CSV lines (e.g. boot messages)
                if line:
                    print(f"  {line}")
                continue

            parts = line[4:].split(",")
            if len(parts) != 4 or parts[0] == "seq":
                continue

            try:
                seq = int(parts[0])
                rssi = int(parts[1])
                drops = int(parts[2])
                rx_count = int(parts[3])
            except ValueError:
                continue

            rssi_history.append(rssi)
            if len(rssi_history) > 100:
                rssi_history.pop(0)

            avg_rssi = sum(rssi_history) / len(rssi_history)
            bar, color, label = draw_bar(rssi)
            loss_pct = (drops / (seq)) * 100 if seq > 0 else 0.0

            sys.stdout.write(
                f"\r{BOLD}[Pkt #{seq:05d}]{RESET} "
                f"RSSI: {color}{rssi:3d} dBm{RESET} "
                f"[{bar}] {color}{label:<12}{RESET} "
                f"Avg: {avg_rssi:5.1f} dBm | "
                f"Loss: {YELLOW if loss_pct > 0 else GREEN}{loss_pct:4.1f}%{RESET} ({drops} drops)  "
            )
            sys.stdout.flush()

    except KeyboardInterrupt:
        print(f"\n\n{PINK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print("Session Summary:")
        if rssi_history:
            print(f"  Min RSSI:  {min(rssi_history)} dBm")
            print(f"  Max RSSI:  {max(rssi_history)} dBm")
            print(f"  Avg RSSI:  {sum(rssi_history)/len(rssi_history):.1f} dBm")
        print(f"{PINK}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
        ser.close()

if __name__ == "__main__":
    main()
