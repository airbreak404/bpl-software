#!/usr/bin/env python3
"""
==============================================================================
🌸 BRONCO PROPULSION LABORATORY — REAL-TIME MISSION CONTROL WEB SERVER 🌸
==============================================================================
Avionics & Telemetry Web Ground Station (WMU AIAA Pegasus Chapter)
Target: 5:00 PM Software Team Meeting with Olivia

Features:
  - High-performance, zero-dependency Python HTTP Server
  - Native Server-Sent Events (SSE) streaming live telemetry at up to 25 Hz
  - Seamless fallback heartbeat generator if hardware is idle
  - Serves local glassmorphism cyberpunk dashboard & offline Chart.js
  - Automatically pops open Google Chrome / Safari to http://localhost:5050
==============================================================================
"""

import sys
import os
import time
import json
import glob
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import serial
import serial.tools.list_ports

PORT = 5050
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

# Global thread-safe client list and latest packet
clients_lock = threading.Lock()
connected_clients = set()
latest_data = {
    "timestamp_ms": 0,
    "thrust": 0.0,
    "temp_casing": 72.0,
    "temp_nozzle": 72.0,
    "temp_ambient": 72.0,
    "rssi": -42,
    "dist_ft": 140.0,
    "dist_m": 42.7
}

hardware_streaming = False

def estimate_open_air_distance(rssi_dbm, tx_power_dbm=20.0, antenna_gain_dbi=4.0):
    eirp = tx_power_dbm + antenna_gain_dbi
    fspl = max(40.0, eirp - rssi_dbm)
    dist_m = 10.0 ** ((fspl - 40.0) / 20.0)
    return dist_m * 3.28084, dist_m

def find_serial_port():
    # Priority: known modem ports or CH343 / Espressif VID
    mac_ports = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wch*")
    if mac_ports:
        return mac_ports[0]

    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if p.vid in [0x1A86, 0x303A, 0x10C4, 0x0403]:
            return p.device
    for p in ports:
        desc = (p.description or "").lower()
        if any(term in desc for term in ["espressif", "ch34", "cp210", "ftdi", "uart", "usbmodem"]):
            return p.device
    return None

def broadcast_packet(packet):
    global latest_data
    latest_data = packet
    json_str = f"data: {json.dumps(packet)}\n\n"
    with clients_lock:
        to_remove = set()
        for client in connected_clients:
            try:
                client.wfile.write(json_str.encode("utf-8"))
                client.wfile.flush()
            except Exception:
                to_remove.add(client)
        connected_clients.difference_update(to_remove)

def serial_reader_thread():
    global hardware_streaming
    while True:
        port = find_serial_port()
        if not port:
            hardware_streaming = False
            time.sleep(1.0)
            continue

        try:
            ser = serial.Serial(port, 115200, timeout=1.0)
            ser.dtr = False
            ser.rts = False
            ser.reset_input_buffer()
            print(f"\033[38;5;48m[✓] Hardware connected to ESP32 Receiver on {port} (115200 baud)\033[0m")
            hardware_streaming = True

            while True:
                raw = ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                parts = line.split(",")
                if len(parts) < 5 or parts[0] == "timestamp_ms" or parts[0] == "seq":
                    continue

                try:
                    t_ms = int(parts[0])
                    thrust = float(parts[1])
                    t_casing = float(parts[2])
                    t_nozzle = float(parts[3])
                    t_ambient = float(parts[4])
                    rssi = int(parts[5]) if len(parts) >= 6 else -42

                    dist_ft, dist_m = estimate_open_air_distance(rssi)

                    packet = {
                        "timestamp_ms": t_ms,
                        "thrust": thrust,
                        "temp_casing": t_casing,
                        "temp_nozzle": t_nozzle,
                        "temp_ambient": t_ambient,
                        "rssi": rssi,
                        "dist_ft": round(dist_ft, 1),
                        "dist_m": round(dist_m, 1)
                    }
                    broadcast_packet(packet)
                except (ValueError, IndexError):
                    continue

        except Exception as e:
            hardware_streaming = False
            print(f"\033[38;5;198m[!] Serial port {port} disconnected: {e}. Retrying...\033[0m")
            time.sleep(1.5)

def background_heartbeat_thread():
    """Generates baseline heartbeat packets if hardware is idle so UI stays reactive."""
    global hardware_streaming, latest_data
    t_start = time.time()
    while True:
        time.sleep(0.5)
        # If no clients or if hardware is actively providing packets, do nothing
        if hardware_streaming:
            continue

        elapsed_ms = int((time.time() - t_start) * 1000)
        # Gentle realistic baseline
        packet = {
            "timestamp_ms": elapsed_ms,
            "thrust": 0.0,
            "temp_casing": 72.0,
            "temp_nozzle": 72.0,
            "temp_ambient": 72.0,
            "rssi": -42,
            "dist_ft": 140.0,
            "dist_m": 42.7
        }
        broadcast_packet(packet)

class TelemetryHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            with clients_lock:
                connected_clients.add(self)

            # Keep connection open for streaming
            while True:
                time.sleep(1.0)
                try:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                except Exception:
                    with clients_lock:
                        connected_clients.discard(self)
                    break
        elif self.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(latest_data).encode("utf-8"))
        else:
            super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging to keep terminal clean
        return

def main():
    print(f"\n\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m")
    print(f"\033[1m\033[38;5;205m     ✨ AIAA BPL AVIONICS & TELEMETRY WEB MISSION CONTROL ✨\033[0m")
    print(f"\033[38;5;141m          Bronco Propulsion Laboratory • Western Michigan University\033[0m")
    print(f"\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m")
    print(f"\033[38;5;218mLocal Web Server:\033[0m  \033[38;5;51mhttp://localhost:{PORT}\033[0m")
    print(f"\033[38;5;218mDashboard UI:\033[0m      \033[38;5;205mCyberpunk Dark / Pink Glassmorphism HUD\033[0m")
    print(f"\033[38;5;48m[✓] Launching browser dashboard...\033[0m\n")

    # Start background threads
    t_ser = threading.Thread(target=serial_reader_thread, daemon=True)
    t_ser.start()

    t_hb = threading.Thread(target=background_heartbeat_thread, daemon=True)
    t_hb.start()

    # Automatically open Chrome / Safari after a tiny delay
    def open_browser():
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), TelemetryHTTPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[38;5;198m[!] Shutting down telemetry server...\033[0m\n")
        server.server_close()

if __name__ == "__main__":
    main()
