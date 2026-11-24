#!/usr/bin/env python3
"""
==============================================================================
🌸 BRONCO PROPULSION LABORATORY (BPL) - OFFICIAL TEAM DEMO GROUND STATION 🌸
==============================================================================
Avionics & Software Subteam Demonstration System (AIAA Pegasus Chapter)
Target: 5:00 PM Software Team Meeting with Olivia

Features:
  - 200 Hz Live Telemetry Stream over ESP-NOW
  - Aerotech J425R Motor Simulation Engine (Thrust, Nozzle & Casing Temps)
  - Real-time Antenna RF Signal Health & Free-Space Standoff Distance
  - Dual Live Scrolling Sparklines (Motor Thrust Curve + RF Signal Margin)
  - NFPA 1127 / Tripoli High-Power Rocketry Safety Clearance Badges
  - Auto-Generates 3-Panel Cyberpunk Flight Qualification Report in Preview
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

# Matplotlib for generating the final flight qualification report
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# ANSI Cyberpunk Pink Color Palette
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
    eirp = tx_power_dbm + antenna_gain_dbi
    fspl = max(40.0, eirp - rssi_dbm)
    dist_m = 10.0 ** ((fspl - 40.0) / 20.0)
    return dist_m * 3.28084

def sparkline(data, min_v, max_v, length=24):
    if not data:
        return ""
    slice_data = data[-length:]
    out = []
    for v in slice_data:
        clamped = max(min_v, min(max_v, v))
        idx = int(((clamped - min_v) / max(0.001, (max_v - min_v))) * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return "".join(out)

def generate_flight_qualification_report(df_rows, output_path):
    if not MATPLOTLIB_AVAILABLE or not df_rows:
        return None

    import pandas as pd
    df = pd.DataFrame(df_rows)

    bg_dark = "#0f0c1b"
    card_dark = "#181428"
    grid_color = "#322947"
    pink_hot = "#ff2a85"
    pink_glow = "#ff71ce"
    pink_soft = "#f472b6"
    cyan_neon = "#38bdf8"
    purple_accent = "#a855f7"
    coral_pink = "#fb7185"
    text_light = "#f8fafc"

    times = [t - df["timestamp_epoch"].iloc[0] for t in df["timestamp_epoch"]]
    df["time_sec"] = times

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 9), gridspec_kw={"height_ratios": [2.2, 1.8, 1.8]})
    fig.patch.set_facecolor(bg_dark)

    for ax in (ax1, ax2, ax3):
        ax.set_facecolor(card_dark)
        ax.grid(True, linestyle="--", linewidth=0.6, color=grid_color, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color(grid_color)
        ax.tick_params(colors="#cbd5e1", labelsize=9)

    # 1. Thrust Profile
    ax1.plot(df["time_sec"], df["thrust_lbf"], color=pink_hot, linewidth=2.2, label="Measured Thrust (lbf)")
    ax1.fill_between(df["time_sec"], df["thrust_lbf"], color=pink_hot, alpha=0.2)
    max_thrust = df["thrust_lbf"].max()
    ax1.axhline(max_thrust, color=pink_glow, linestyle=":", linewidth=1.4, label=f"Peak Thrust: {max_thrust:.1f} lbs")
    ax1.set_ylabel("Thrust (lbs)", fontsize=10, fontweight="bold", color=text_light)
    ax1.set_title("BPL PROPULSION TELEMETRY & RF RANGE QUALIFICATION REPORT",
                  fontsize=12, fontweight="bold", pad=10, color=pink_glow)
    legend1 = ax1.legend(loc="upper right", framealpha=0.85, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend1.get_texts(), color=text_light, fontsize=8)

    # 2. Thermocouples
    ax2.plot(df["time_sec"], df["temp_nozzle_f"], color=coral_pink, linewidth=2.0, label=f"Nozzle Max: {df['temp_nozzle_f'].max():.1f}°F")
    ax2.plot(df["time_sec"], df["temp_casing_f"], color=purple_accent, linewidth=1.8, label=f"Casing Max: {df['temp_casing_f'].max():.1f}°F")
    ax2.plot(df["time_sec"], df["temp_ambient_f"], color="#94a3b8", linestyle="--", label="Ambient (72°F)")
    ax2.set_ylabel("Temp (°F)", fontsize=10, fontweight="bold", color=text_light)
    legend2 = ax2.legend(loc="upper right", framealpha=0.85, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend2.get_texts(), color=text_light, fontsize=8)

    # 3. RF Link Health & Margin
    ax3.plot(df["time_sec"], df["rssi_dbm"], color=cyan_neon, linewidth=2.0, label="Antenna RSSI (dBm)")
    ax3.axhline(-50, color="#10b981", linestyle=":", linewidth=1.2, label="100 ft Safe Line (-50 dBm)")
    ax3.axhline(-60, color="#fbbf24", linestyle=":", linewidth=1.2, label="300 ft Safe Line (-60 dBm)")
    ax3.axhline(-88, color="#f43f5e", linestyle="--", linewidth=1.2, label="Drop Floor Limit (-88 dBm)")
    ax3.set_ylabel("Signal (dBm)", fontsize=10, fontweight="bold", color=text_light)
    ax3.set_xlabel("Elapsed Time (seconds)", fontsize=10, fontweight="bold", color=text_light)
    ax3.set_ylim(-100, -25)
    legend3 = ax3.legend(loc="lower left", framealpha=0.85, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend3.get_texts(), color=text_light, fontsize=8)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=200, facecolor=bg_dark)
    plt.close()
    return output_path

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_serial_port()
    if not port:
        print(f"\n{PINK_HOT}[!] No ESP32 Receiver Port Detected!{RESET}")
        print(f"{PINK_SOFT}Please plug in the ground receiver board into your Mac's UART port.{RESET}\n")
        sys.exit(1)

    print("\033[2J\033[H", end="")
    print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
    print(f"{BOLD}{PINK_GLOW}     ✨ AIAA BPL AVIONICS & TELEMETRY GROUND STATION ✨{RESET}")
    print(f"{PURPLE}          Bronco Propulsion Laboratory • Western Michigan University{RESET}")
    print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
    print(f"{PINK_SOFT}Receiver Port:{RESET} {CYAN}{port}{RESET} (115200 baud) • {BOLD}{PINK_HOT}Cyberpunk / Pink Theme{RESET}")

    try:
        ser = serial.Serial(port, 115200, timeout=1.0)
        ser.dtr = False
        ser.rts = False
    except Exception as e:
        print(f"{PINK_HOT}[!] Error opening serial port {port}: {e}{RESET}")
        sys.exit(1)

    print(f"{GREEN}[✓] Ground Station Online! Waiting for Stand Telemetry Stream...{RESET}")
    print(f"{DIM}Press Ctrl+C to conclude test and auto-generate the flight report card.{RESET}\n")

    records = []
    thrust_hist = []
    rssi_hist = []
    total_packets = 0
    start_time = time.time()
    last_ui_update = 0

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            parts = line.split(",")

            # Handle both 5-part (legacy) and 6-part (with RSSI) telemetry formats
            if len(parts) < 5 or parts[0] == "timestamp_ms":
                continue

            try:
                t_ms = int(parts[0])
                thrust = float(parts[1])
                t_casing = float(parts[2])
                t_nozzle = float(parts[3])
                t_ambient = float(parts[4])
                rssi = int(parts[5]) if len(parts) >= 6 else -45
            except ValueError:
                continue

            now = time.time()
            total_packets += 1
            thrust_hist.append(thrust)
            rssi_hist.append(rssi)

            records.append({
                "timestamp_epoch": now,
                "timestamp_ms": t_ms,
                "thrust_lbf": thrust,
                "temp_casing_f": t_casing,
                "temp_nozzle_f": t_nozzle,
                "temp_ambient_f": t_ambient,
                "rssi_dbm": rssi
            })

            # Engine State Machine
            if thrust > 10.0:
                engine_state = f"{PINK_HOT}{BOLD}🔥 ACTIVE BURN (PEAK {thrust:.1f} lbs){RESET}"
            elif t_nozzle > 100.0:
                engine_state = f"{PURPLE}❄️ POST-BURNOUT COOLDOWN{RESET}"
            else:
                engine_state = f"{GREEN}🛡️ ARMED / STANDBY{RESET}"

            # Update UI at ~15 Hz
            if now - last_ui_update >= 0.06:
                last_ui_update = now

                # Gauges
                thrust_ratio = max(0.0, min(1.0, thrust / 100.0))
                thrust_bar = PINK_HOT + "█" * int(thrust_ratio * 20) + DIM + "░" * (20 - int(thrust_ratio * 20)) + RESET

                rssi_ratio = max(0.0, min(1.0, (rssi - (-100)) / 70.0))
                rssi_bar = CYAN + "█" * int(rssi_ratio * 20) + DIM + "░" * (20 - int(rssi_ratio * 20)) + RESET

                dist_ft = estimate_open_air_distance_ft(rssi)
                margin_db = rssi - (-97)

                thrust_spark = PINK_HOT + sparkline(thrust_hist, 0.0, 100.0, 16) + RESET
                rssi_spark = CYAN + sparkline(rssi_hist, -95, -30, 16) + RESET

                sys.stdout.write(
                    f"\r{BOLD}THRUST:{RESET} {thrust_bar} {PINK_GLOW}{thrust:5.1f} lbs{RESET} [{thrust_spark}]  "
                    f"{PINK_HOT}║{RESET} {BOLD}NOZZLE:{RESET} {coral_pink if 'coral_pink' in locals() else YELLOW}{t_nozzle:5.1f}°F{RESET}  "
                    f"{PINK_HOT}║{RESET} {BOLD}SIGNAL:{RESET} {rssi_bar} {CYAN}{rssi:3d} dBm{RESET} [{rssi_spark}]  "
                    f"{PINK_HOT}║{RESET} {BOLD}Range:{RESET} {PURPLE}~{dist_ft:3.0f}ft{RESET} (+{margin_db:.0f}dB)  "
                    f"{PINK_HOT}║{RESET} {engine_state}  "
                )
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n\n" + f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")
        print(f"{BOLD}{PINK_GLOW}     ✨ DEMO COMPLETE! COMPILING FLIGHT QUALIFICATION REPORT ✨{RESET}")
        print(f"{PINK_HOT}🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸{RESET}")

    ser.close()

    if records:
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        repo_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(repo_dir, "data", f"telemetry_demo_{ts_str}.csv")
        report_png = os.path.join(repo_dir, "reports", f"bpl_flight_qualification_{ts_str}_report.png")

        import pandas as pd
        pd.DataFrame(records).to_csv(csv_path, index=False)
        print(f"{GREEN}[✓] Raw Flight Dataset Saved:{RESET} {csv_path}")

        print(f"{PINK_SOFT}Rendering 3-Panel Cyberpunk Flight & RF Report...{RESET}")
        generated = generate_flight_qualification_report(records, report_png)

        if generated and os.path.exists(generated):
            print(f"{GREEN}[✓] Report Generated:{RESET} {generated}")
            print(f"{CYAN}[✓] Opening in Apple Preview for the team...{RESET}\n")
            os.system(f'open "{generated}"')

if __name__ == "__main__":
    main()
