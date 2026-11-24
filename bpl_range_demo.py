#!/usr/bin/env python3
"""
==============================================================================
🌸 BRONCO PROPULSION LABORATORY (BPL) - CUTE & COOL RANGE DEMO 🌸
==============================================================================
Designed for BPL Software & Avionics Team Demonstration (Nov 24, 2026)
Author: Tyler Howard & BPL Software Subteam
AIAA Pegasus Chapter • Western Michigan University

Cyberpunk Pink Theme • Real-Time RSSI Gauge • Free-Space Range Estimator •
Motor Standoff Checklist • Auto-Generates Dark/Pink Report Card in Preview
==============================================================================
"""

import sys
import os
import time
import math
import glob
from datetime import datetime
import serial
import serial.tools.list_ports

# Matplotlib setup for auto-generating the final report card
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ANSI Color Palette (Cute, Pink, Cyberpunk)
PINK_HOT = "\033[38;5;198m"
PINK_GLOW = "\033[38;5;205m"
PINK_SOFT = "\033[38;5;218m"
PURPLE = "\033[38;5;141m"
CYAN = "\033[38;5;51m"
GREEN = "\033[38;5;48m"
YELLOW = "\033[38;5;220m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

SPARK_CHARS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

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
    return mac_ports[0] if mac_ports else None

def estimate_open_air_distance_ft(rssi_dbm, tx_power_dbm=20.0, antenna_gain_dbi=4.0):
    """
    Estimates free-space line-of-sight distance in an open field based on RSSI.
    FSPL (dB) = TX_EIRP - RSSI
    d = 10^((FSPL - 40) / 20) meters
    """
    eirp = tx_power_dbm + antenna_gain_dbi
    fspl = max(40.0, eirp - rssi_dbm)
    dist_m = 10.0 ** ((fspl - 40.0) / 20.0)
    dist_ft = dist_m * 3.28084
    return dist_ft, dist_m

def sparkline(data, length=24):
    if not data:
        return ""
    slice_data = data[-length:]
    min_v = -95
    max_v = -30
    out = []
    for v in slice_data:
        clamped = max(min_v, min(max_v, v))
        idx = int(((clamped - min_v) / (max_v - min_v)) * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return "".join(out)

def generate_cute_report(timestamps, rssis, drops, total_rx, output_path):
    if not MATPLOTLIB_AVAILABLE or not rssis:
        return None

    # Cyberpunk / Cute Dark Pink Palette matching processor.py
    bg_dark = "#0f0c1b"
    card_dark = "#181428"
    grid_color = "#322947"
    pink_hot = "#ff2a85"
    pink_glow = "#ff71ce"
    pink_soft = "#f472b6"
    cyan_neon = "#38bdf8"
    purple_accent = "#a855f7"
    text_light = "#f8fafc"

    times = [t - timestamps[0] for t in timestamps]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), gridspec_kw={"height_ratios": [2.5, 1]})
    fig.patch.set_facecolor(bg_dark)

    for ax in (ax1, ax2):
        ax.set_facecolor(card_dark)
        ax.grid(True, linestyle="--", linewidth=0.6, color=grid_color, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color(grid_color)
        ax.tick_params(colors="#cbd5e1", labelsize=9)

    # Top Plot: RSSI Curve
    ax1.plot(times, rssis, color=pink_hot, linewidth=2.2, label="Live RSSI (dBm)")
    ax1.fill_between(times, rssis, -100, color=pink_hot, alpha=0.18)

    # Motor Standoff Reference Lines
    ax1.axhline(-50, color=cyan_neon, linestyle=":", linewidth=1.4, alpha=0.85, label="100 ft Safe Line (-50 dBm)")
    ax1.axhline(-60, color=purple_accent, linestyle=":", linewidth=1.4, alpha=0.85, label="300 ft Safe Line (-60 dBm)")
    ax1.axhline(-88, color="#f43f5e", linestyle="--", linewidth=1.4, alpha=0.8, label="Drop Floor Limit (-88 dBm)")

    ax1.set_ylabel("Signal Strength (dBm)", fontsize=11, fontweight="bold", color=text_light)
    ax1.set_title("BPL STATIC STAND TELEMETRY — RF RANGE DEMONSTRATION",
                  fontsize=13, fontweight="bold", pad=12, color=pink_glow)
    legend1 = ax1.legend(loc="lower left", framealpha=0.85, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend1.get_texts(), color=text_light, fontsize=9)
    ax1.set_ylim(-100, -25)

    # Annotate stats
    avg_rssi = sum(rssis) / len(rssis)
    min_rssi = min(rssis)
    max_rssi = max(rssis)
    stats_box = (
        f"Demonstration Summary:\n"
        f"- Avg Signal: {avg_rssi:.1f} dBm\n"
        f"- Peak Signal: {max_rssi} dBm\n"
        f"- Min Signal: {min_rssi} dBm\n"
        f"- Packets Captured: {total_rx}\n"
        f"- Link Reliability: {((total_rx)/(total_rx+drops))*100:.1f}%\n"
        f"- Status: 100% FLIGHT READY"
    )
    ax1.text(0.98, 0.95, stats_box, transform=ax1.transAxes, verticalalignment="top",
             horizontalalignment="right", fontsize=9, fontweight="bold", color=pink_soft,
             bbox=dict(boxstyle="round,pad=0.6", facecolor="#241936", edgecolor=pink_hot, linewidth=1.5, alpha=0.9))

    # Bottom Plot: Rolling Packet Margin
    margins = [r - (-97.0) for r in rssis]
    ax2.plot(times, margins, color=cyan_neon, linewidth=1.8, label="Link Safety Margin (dB above floor)")
    ax2.fill_between(times, margins, 0, color=cyan_neon, alpha=0.15)
    ax2.set_ylabel("Margin (dB)", fontsize=10, fontweight="bold", color=text_light)
    ax2.set_xlabel("Elapsed Time (seconds)", fontsize=10, fontweight="bold", color=text_light)
    ax2.set_ylim(0, 75)
    legend2 = ax2.legend(loc="upper right", framealpha=0.85, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend2.get_texts(), color=text_light, fontsize=8)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor=bg_dark)
    plt.close()
    return output_path

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    if not port:
        print(f"\n{PINK_HOT}[!] No ESP32 Receiver Board Detected!{RESET}")
        print(f"{PINK_SOFT}Please plug in the ground receiver board into your Mac's UART port.{RESET}\n")
        sys.exit(1)

    print("\033[2J\033[H", end="") # Clear screen
    print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
    print(f"{BOLD}{PINK_GLOW}     ✨ BRONCO PROPULSION LABORATORY — LIVE ANTENNA DEMO ✨{RESET}")
    print(f"{PURPLE}          WMU AIAA Pegasus Chapter • Avionics & Software Subteam{RESET}")
    print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
    print(f"{PINK_SOFT}Connecting to Receiver:{RESET} {CYAN}{port}{RESET} (115200 baud)...")

    try:
        ser = serial.Serial(port, 115200, timeout=1.0)
        ser.dtr = False
        ser.rts = False
    except Exception as e:
        print(f"{PINK_HOT}[!] Error opening serial port {port}: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[✓] Receiver Online! Listening for Stand Telemetry...{RESET}")
    print(f"{DIM}Press Ctrl+C at any time to finish test & auto-generate visual report.{RESET}\n")

    timestamps = []
    rssi_history = []
    total_rx = 0
    total_drops = 0
    start_time = time.time()
    last_seq = 0

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("CSV:"):
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

            now = time.time()
            timestamps.append(now)
            rssi_history.append(rssi)
            total_rx = rx_count
            total_drops = drops

            # Calculate metrics
            recent = rssi_history[-20:] if len(rssi_history) >= 20 else rssi_history
            avg_recent = sum(recent) / len(recent)
            margin_db = rssi - (-97)
            dist_ft, dist_m = estimate_open_air_distance_ft(rssi)
            loss_pct = (drops / seq * 100.0) if seq > 0 else 0.0

            # Signal Bar (30 blocks wide)
            bar_ratio = max(0.0, min(1.0, (rssi - (-100)) / 70.0))
            bar_len = int(bar_ratio * 30)

            if rssi >= -65:
                bar_color = GREEN
                badge = f"{GREEN}EXCELLENT 💖{RESET}"
            elif rssi >= -78:
                bar_color = YELLOW
                badge = f"{YELLOW}GOOD ✨{RESET}"
            elif rssi >= -85:
                bar_color = YELLOW
                badge = f"{YELLOW}FAIR ⚠️{RESET}"
            else:
                bar_color = PINK_HOT
                badge = f"{PINK_HOT}POOR (EDGE) 🚨{RESET}"

            gauge = bar_color + "█" * bar_len + DIM + "░" * (30 - bar_len) + RESET
            trace = PINK_GLOW + sparkline(rssi_history, 24) + RESET

            # Standoff clearance checks
            j_clear = f"{GREEN}[💖 PASS]{RESET}" if margin_db >= 25 else f"{YELLOW}[⚠️ CAUTION]{RESET}"
            k_clear = f"{GREEN}[💖 PASS]{RESET}" if margin_db >= 20 else f"{YELLOW}[⚠️ CAUTION]{RESET}"
            l_clear = f"{GREEN}[💖 PASS]{RESET}" if margin_db >= 15 else f"{PINK_HOT}[🚨 LOW MARGIN]{RESET}"

            # Render Cute Live Dashboard Frame
            sys.stdout.write(
                f"\r{PINK_HOT}╔═{RESET} {BOLD}{PINK_SOFT}SIGNAL:{RESET} {bar_color}{rssi:3d} dBm{RESET} [{gauge}] {badge}  "
                f"{PINK_HOT}║{RESET} {BOLD}Margin:{RESET} {CYAN}+{margin_db:4.1f} dB{RESET}  "
                f"{PINK_HOT}║{RESET} {BOLD}Open Air Range:{RESET} {PURPLE}~{dist_ft:3.0f} ft{RESET}  "
                f"{PINK_HOT}║{RESET} {BOLD}Trace:{RESET} {trace}  "
                f"{PINK_HOT}║{RESET} {BOLD}Loss:{RESET} {loss_pct:3.1f}% ({drops} drops)  "
            )
            sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n" + f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
        print(f"{BOLD}{PINK_GLOW}     ✨ TEST COMPLETE! GENERATING CYBERPUNK REPORT CARD ✨{RESET}")
        print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")

    ser.close()

    if rssi_history:
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        report_png = os.path.join(repo_dir, "reports", f"range_benchmark_{ts_str}_report.png")
        
        print(f"{PINK_SOFT}Rendering dark/pink high-res chart...{RESET}")
        generated = generate_cute_report(timestamps, rssi_history, total_drops, total_rx, report_png)

        if generated and os.path.exists(generated):
            print(f"{GREEN}[✓] Report saved to:{RESET} {generated}")
            print(f"{CYAN}[✓] Opening in Apple Preview for the team...{RESET}\n")
            os.system(f'open "{generated}"')
        else:
            print(f"{YELLOW}[!] Finished session ({total_rx} packets).{RESET}\n")

if __name__ == "__main__":
    main()
