#!/usr/bin/env python3
"""
==============================================================================
Bronco Propulsion Laboratory (BPL) - Antenna RF Comprehensive Data Logger
==============================================================================
Logs live RF packets from the ESP32 receiver to CSV and tracks:
  - High-res RSSI time series
  - Packet drop events
  - Distance checkpoints & annotations
  - Rolling statistics (mean, median, std dev, min, max)
==============================================================================
"""

import sys
import os
import time
import json
import glob
from datetime import datetime
import serial
import serial.tools.list_ports

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

def main():
    port = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else find_serial_port()
    duration = None
    for arg in sys.argv:
        if arg.startswith("--duration="):
            duration = float(arg.split("=")[1])

    if not port:
        print("[!] No ESP32 serial port detected.")
        sys.exit(1)

    repo_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(repo_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join(data_dir, f"antenna_benchmark_{timestamp_str}.csv")
    json_filename = os.path.join(data_dir, "live_antenna_stats.json")

    print(f"=======================================================")
    print(f"  BPL ANTENNA RF COMPREHENSIVE DATA LOGGER")
    print(f"=======================================================")
    print(f"Port:       {port}")
    print(f"Output CSV: {csv_filename}")
    print(f"Live JSON:  {json_filename}")
    if duration:
        print(f"Duration:   {duration:.1f} seconds")
    print(f"=======================================================\n")

    try:
        ser = serial.Serial(port, 115200, timeout=1.0)
        ser.dtr = False
        ser.rts = False
    except Exception as e:
        print(f"[!] Error opening serial port {port}: {e}")
        sys.exit(1)

    rssi_history = []
    total_rx = 0
    total_drops = 0
    start_time = time.time()
    last_print = 0

    with open(csv_filename, "w") as f:
        f.write("timestamp_epoch,iso_time,packet_seq,rssi_dbm,dropped_packets,total_received,loss_rate_pct\n")

        try:
            while True:
                now = time.time()
                if duration and (now - start_time) >= duration:
                    print(f"\n[✓] Completed duration of {duration:.1f}s.")
                    break

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

                total_rx = rx_count
                total_drops = drops
                rssi_history.append(rssi)
                loss_pct = (drops / seq * 100.0) if seq > 0 else 0.0
                iso_now = datetime.now().isoformat()

                # Write record
                f.write(f"{now:.3f},{iso_now},{seq},{rssi},{drops},{rx_count},{loss_pct:.2f}\n")
                if total_rx % 10 == 0:
                    f.flush()

                # Periodic terminal update every 1 second
                if now - last_print >= 1.0:
                    last_print = now
                    recent = rssi_history[-20:] if len(rssi_history) >= 20 else rssi_history
                    avg_recent = sum(recent) / len(recent) if recent else rssi
                    
                    if avg_recent >= -65:
                        quality = "EXCELLENT"
                    elif avg_recent >= -78:
                        quality = "GOOD"
                    elif avg_recent >= -85:
                        quality = "FAIR / WEAK"
                    else:
                        quality = "POOR (DROP-OUT)"

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Pkt #{seq:05d} | RSSI: {rssi:3d} dBm (Avg: {avg_recent:5.1f} dBm) | "
                          f"Quality: {quality:<12} | "
                          f"Loss: {loss_pct:4.1f}% ({drops} dropped / {total_rx} rx)")

                    # Write live JSON snapshot
                    stats = {
                        "session_id": timestamp_str,
                        "elapsed_seconds": round(now - start_time, 1),
                        "total_received": total_rx,
                        "total_dropped": total_drops,
                        "loss_rate_pct": round(loss_pct, 2),
                        "current_rssi": rssi,
                        "avg_rssi": round(sum(rssi_history) / len(rssi_history), 1) if rssi_history else 0,
                        "min_rssi": min(rssi_history) if rssi_history else 0,
                        "max_rssi": max(rssi_history) if rssi_history else 0,
                        "quality": quality,
                        "csv_file": csv_filename
                    }
                    try:
                        with open(json_filename, "w") as jf:
                            json.dump(stats, jf, indent=2)
                    except Exception:
                        pass

        except KeyboardInterrupt:
            print("\n[!] Logging stopped by user.")

    ser.close()

    if rssi_history:
        print("\n" + "=" * 60)
        print("  SESSION BENCHMARK SUMMARY")
        print("=" * 60)
        print(f"  Duration:         {time.time() - start_time:.1f} seconds")
        print(f"  Packets Received: {total_rx}")
        print(f"  Packets Dropped:  {total_drops} ({total_drops/max(1, total_rx+total_drops)*100:.2f}%)")
        print(f"  Min Signal:       {min(rssi_history)} dBm")
        print(f"  Max Signal:       {max(rssi_history)} dBm")
        print(f"  Avg Signal:       {sum(rssi_history)/len(rssi_history):.1f} dBm")
        print(f"  Saved Dataset:    {csv_filename}")
        print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
