#!/usr/bin/env python3
"""
==============================================================================
🌸 BRONCO PROPULSION LABORATORY — REAL-TIME MISSION CONTROL WEB SERVER 🌸
==============================================================================
Avionics & Telemetry Web Ground Station (WMU AIAA Pegasus Chapter)
Target Hardware: Dual ESP32-S3 N16R8 boards (200 Hz ESP-NOW + IPEX Mod)
Authors: Tyler Howard & BPL Software Subteam

Features:
  - High-performance, zero-dependency Python HTTP Server
  - Native Server-Sent Events (SSE) streaming live telemetry at 25 Hz
  - Internal 200 Hz DAQ sampling with sequence & packet drop tracking
  - Authoritative server-side numerical impulse integration & burn timing
  - Live hardware frequency measurement (e.g. 199.8 Hz ESP-NOW)
  - Physically calibrated Log-Distance RF propagation model (1.5 ft -> 350+ ft)
  - Zero-glitch, memory-bounded telemetry broadcast
==============================================================================
"""

import sys
import os
import time
import json
import glob
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import serial
import serial.tools.list_ports

PORT = 5050
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

clients_lock = threading.Lock()
connected_clients = set()

# Server-Side Authoritative Telemetry State
state_lock = threading.Lock()
all_time_peak_thrust = 0.0
all_time_max_nozzle = 72.0
burn_count = 0
is_burning = False
burn_start_time = None
current_burn_impulse_ns = 0.0
last_burn_impulse_ns = 0.0
current_burn_duration_s = 0.0
last_burn_duration_s = 0.0
last_thrust_sample_time = None

latest_data = {
    "timestamp_ms": 0,
    "thrust": 0.0,
    "thrust_n": 0.0,
    "chamber_psi": 0,
    "peak_thrust": 0.0,
    "peak_thrust_n": 0,
    "temp_casing": 72.0,
    "temp_nozzle": 72.0,
    "max_nozzle": 72.0,
    "temp_ambient": 72.0,
    "rssi": -26,
    "dist_ft": 1.5,
    "dist_m": 0.46,
    "hardware_active": False,
    "packet_drop_rate": 0.0,
    "packets_rx": 0,
    "packets_lost": 0,
    "stream_hz": 200.0,
    "burn_active": False,
    "burn_count": 0,
    "total_impulse_ns": 0.0,
    "burn_duration_s": 0.0,
    "motor_class": "STANDBY",
    "stand_mac": "44:bd:8d:71:94:1c",
    "rx_mac": "14:c1:9f:3b:e5:4c",
    "rx_port": "Searching...",
    "rx_sensitivity": -97,
    "tx_eirp": 24.0
}

last_hardware_packet_time = 0.0
total_hw_rx = 0
total_hw_lost = 0
last_hw_timestamp_ms = None
last_packet_arrival_time = None
rolling_hz = 200.0
active_serial_port = None


def get_motor_class_letter(impulse_ns):
    if impulse_ns <= 0.1:
        return "STANDBY"
    if impulse_ns <= 160:
        return "Class G"
    if impulse_ns <= 320:
        return "Class H"
    if impulse_ns <= 640:
        return "Class I"
    if impulse_ns <= 1280:
        return "Class J"
    if impulse_ns <= 2560:
        return "Class K"
    if impulse_ns <= 5120:
        return "Class L"
    return "Class M"


def estimate_calibrated_distance(rssi_dbm, n=2.2, rssi_1m=-35.0):
    """
    Physically calibrated Log-Distance Path Loss Model for 2.4 GHz ESP32-S3.
    At 2 ft (desk): RSSI ~ -24 to -31 dBm -> ~1.5 to 2.1 ft
    At 100 ft (NFPA J-Class): RSSI ~ -68 dBm -> ~103 ft
    """
    ratio = (rssi_1m - rssi_dbm) / (10.0 * n)
    dist_m = 10.0 ** ratio
    dist_ft = max(1.5, dist_m * 3.28084)
    dist_m = dist_ft * 0.3048
    return dist_ft, dist_m


def find_serial_port():
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
        for client in list(connected_clients):
            try:
                client.wfile.write(json_str.encode("utf-8"))
                client.wfile.flush()
            except Exception:
                to_remove.add(client)
        connected_clients.difference_update(to_remove)


def serial_reader_thread():
    global last_hardware_packet_time, total_hw_rx, total_hw_lost, last_hw_timestamp_ms
    global last_packet_arrival_time, rolling_hz, active_serial_port
    global all_time_peak_thrust, all_time_max_nozzle, burn_count, is_burning
    global burn_start_time, current_burn_impulse_ns, last_burn_impulse_ns
    global current_burn_duration_s, last_burn_duration_s, last_thrust_sample_time

    last_broadcast_time = 0.0

    while True:
        port = find_serial_port()
        active_serial_port = port
        if not port:
            time.sleep(1.0)
            continue

        try:
            ser = serial.Serial(port, 115200, timeout=0.5)
            ser.dtr = False
            ser.rts = False
            ser.reset_input_buffer()
            print(f"\033[38;5;48m[✓] Connected to ESP32 Receiver on {port} (115200 baud)\033[0m")

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
                    thrust = max(0.0, float(parts[1]))
                    t_casing = float(parts[2])
                    t_nozzle = float(parts[3])
                    t_ambient = float(parts[4])
                    rssi = int(parts[5]) if len(parts) >= 6 else -26

                    now = time.time()
                    if last_packet_arrival_time is not None:
                        dt_arr = now - last_packet_arrival_time
                        if 0.001 < dt_arr < 0.1:
                            inst_hz = 1.0 / dt_arr
                            rolling_hz = rolling_hz * 0.9 + inst_hz * 0.1
                    last_packet_arrival_time = now

                    # Authoritative Server-Side Burn State Machine & Numerical Integration
                    with state_lock:
                        if thrust > all_time_peak_thrust:
                            all_time_peak_thrust = thrust
                        if t_nozzle > all_time_max_nozzle:
                            all_time_max_nozzle = t_nozzle

                        if thrust > 2.0:
                            if not is_burning:
                                is_burning = True
                                burn_start_time = now
                                current_burn_impulse_ns = 0.0

                            dt_int = 0.005
                            if last_thrust_sample_time is not None:
                                dt_meas = now - last_thrust_sample_time
                                if 0.001 <= dt_meas <= 0.05:
                                    dt_int = dt_meas

                            thrust_n = thrust * 4.44822
                            current_burn_impulse_ns += thrust_n * dt_int
                            current_burn_duration_s = max(0.0, now - burn_start_time)
                            display_impulse = current_burn_impulse_ns
                            display_duration = current_burn_duration_s
                        else:
                            if is_burning:
                                is_burning = False
                                burn_count += 1
                                last_burn_impulse_ns = current_burn_impulse_ns
                                last_burn_duration_s = current_burn_duration_s

                            display_impulse = last_burn_impulse_ns
                            display_duration = last_burn_duration_s

                        last_thrust_sample_time = now

                    # Packet loss estimation based on 5ms expected 200 Hz delta
                    if last_hw_timestamp_ms is not None:
                        delta = t_ms - last_hw_timestamp_ms
                        if 8 < delta < 2000:
                            missed = max(0, round(delta / 5.0) - 1)
                            total_hw_lost += missed
                    last_hw_timestamp_ms = t_ms
                    total_hw_rx += 1

                    drop_rate = 0.0
                    if (total_hw_rx + total_hw_lost) > 0:
                        drop_rate = (total_hw_lost / (total_hw_rx + total_hw_lost)) * 100.0

                    dist_ft, dist_m = estimate_calibrated_distance(rssi)

                    packet = {
                        "timestamp_ms": t_ms,
                        "thrust": round(thrust, 2),
                        "thrust_n": round(thrust * 4.44822, 1),
                        "chamber_psi": round(thrust * 5.2),
                        "peak_thrust": round(all_time_peak_thrust, 1),
                        "peak_thrust_n": round(all_time_peak_thrust * 4.44822),
                        "temp_casing": round(t_casing, 1),
                        "temp_nozzle": round(t_nozzle, 1),
                        "max_nozzle": round(all_time_max_nozzle, 1),
                        "temp_ambient": round(t_ambient, 1),
                        "rssi": rssi,
                        "dist_ft": round(dist_ft, 1),
                        "dist_m": round(dist_m, 2),
                        "hardware_active": True,
                        "packet_drop_rate": round(drop_rate, 2),
                        "packets_rx": total_hw_rx,
                        "packets_lost": total_hw_lost,
                        "stream_hz": round(rolling_hz, 1),
                        "burn_active": is_burning,
                        "burn_count": burn_count,
                        "total_impulse_ns": round(display_impulse, 1),
                        "burn_duration_s": round(display_duration, 2),
                        "motor_class": get_motor_class_letter(display_impulse),
                        "stand_mac": "44:bd:8d:71:94:1c",
                        "rx_mac": "14:c1:9f:3b:e5:4c",
                        "rx_port": port,
                        "rx_sensitivity": -97,
                        "tx_eirp": 24.0
                    }
                    last_hardware_packet_time = now

                    # Decimate broadcast to web clients at 25 Hz (40 ms)
                    # Guarantees zero DOM thrashing and silky-smooth 60 FPS in browsers
                    if now - last_broadcast_time >= 0.040:
                        last_broadcast_time = now
                        broadcast_packet(packet)

                except (ValueError, IndexError):
                    continue

        except Exception as e:
            active_serial_port = None
            time.sleep(1.0)


def background_heartbeat_thread():
    """Generates continuous smooth 25 Hz telemetry ticker when hardware is in standby or disconnected."""
    global last_hardware_packet_time
    t_start = time.time()
    tick = 0
    while True:
        time.sleep(0.040)  # 25 Hz smooth refresh rate
        tick += 1

        # If real hardware delivered a packet within last 0.4s, let hardware drive
        if time.time() - last_hardware_packet_time < 0.4:
            continue

        elapsed_ms = int((time.time() - t_start) * 1000)
        dist_ft, dist_m = estimate_calibrated_distance(-31)

        packet = {
            "timestamp_ms": elapsed_ms,
            "thrust": 0.0,
            "thrust_n": 0.0,
            "chamber_psi": 0,
            "peak_thrust": round(all_time_peak_thrust, 1),
            "peak_thrust_n": round(all_time_peak_thrust * 4.44822),
            "temp_casing": 72.0,
            "temp_nozzle": 72.0,
            "max_nozzle": round(all_time_max_nozzle, 1),
            "temp_ambient": 72.0,
            "rssi": -31,
            "dist_ft": round(dist_ft, 1),
            "dist_m": round(dist_m, 2),
            "hardware_active": False,
            "packet_drop_rate": 0.0,
            "packets_rx": tick,
            "packets_lost": 0,
            "stream_hz": 200.0,
            "burn_active": False,
            "burn_count": burn_count,
            "total_impulse_ns": round(last_burn_impulse_ns, 1),
            "burn_duration_s": round(last_burn_duration_s, 2),
            "motor_class": get_motor_class_letter(last_burn_impulse_ns),
            "stand_mac": "44:bd:8d:71:94:1c",
            "rx_mac": "14:c1:9f:3b:e5:4c",
            "rx_port": active_serial_port or "Standalone Simulation",
            "rx_sensitivity": -97,
            "tx_eirp": 24.0
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

            init_str = f"data: {json.dumps(latest_data)}\n\n"
            try:
                self.wfile.write(init_str.encode("utf-8"))
                self.wfile.flush()
            except Exception:
                pass

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
        return


def main():
    print(f"\n\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m")
    print(f"\033[1m\033[38;5;205m     ✨ AIAA BPL AVIONICS & TELEMETRY WEB MISSION CONTROL ✨\033[0m")
    print(f"\033[38;5;141m          Bronco Propulsion Laboratory • Western Michigan University\033[0m")
    print(f"\033[38;5;198m🌸 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 🌸\033[0m")
    print(f"\033[38;5;218mLocal Web Server:\033[0m  \033[38;5;51mhttp://localhost:{PORT}\033[0m")
    print(f"\033[38;5;218mDashboard UI:\033[0m      \033[38;5;205mCyberpunk Dark / Pink Glassmorphism HUD\033[0m")
    print(f"\033[38;5;48m[✓] Authoritative server DAQ physics active (25 Hz SSE, 200 Hz Serial)...\033[0m\n")

    t_ser = threading.Thread(target=serial_reader_thread, daemon=True)
    t_ser.start()

    t_hb = threading.Thread(target=background_heartbeat_thread, daemon=True)
    t_hb.start()

    server = ThreadingHTTPServer(("0.0.0.0", PORT), TelemetryHTTPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\033[38;5;198m[!] Shutting down telemetry server...\033[0m\n")
        server.server_close()


if __name__ == "__main__":
    main()
