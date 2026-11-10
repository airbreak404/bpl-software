# BPL Ground Station & Live Telemetry Monitor
# Listens for sensor readings from the test stand over USB Serial or Wi-Fi and logs everything to CSV.
# Supports 2-board wireless link (ESP-NOW receiver plugged into laptop via USB).
# Author: Tyler Howard & Sofia Martinez (Software Subteam)

import sys
import os
import time
import argparse
import socket
import glob
import pandas as pd
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

# Enable ANSI colors on Windows terminals
if os.name == "nt":
    os.system("")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_esp32_serial_port():
    """Finds the USB serial port for the ESP32 receiver on your computer (Windows, macOS, Linux)."""
    if not SERIAL_AVAILABLE:
        return None

    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    # 1. Match by Vendor/Product ID (most robust cross-platform for Windows & Mac)
    # WCH CH342/CH343: VID 0x1A86 (6790), Espressif: VID 0x303A, CP210x: VID 0x10C4, FTDI: VID 0x0403
    for p in ports:
        if p.vid in [0x1A86, 0x303A, 0x10C4, 0x0403]:
            return p.device

    # 2. Match by description/name keywords
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        combined = f"{desc} {hwid} {p.device.lower()}"
        if any(term in combined for term in ["espressif", "ch34", "cp210", "ftdi", "uart", "usbmodem", "usbserial", "wchusbserial"]):
            return p.device

    # 3. If running on Windows (or only 1 serial device connected), auto-select it
    if len(ports) == 1:
        return ports[0].device

    # 4. Fallback direct filesystem glob on macOS
    mac_ports = glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.wchusbserial*")
    if mac_ports:
        return mac_ports[0]

    return None

def listen_serial(port_name, baud=115200, log_path="telemetry.csv", udp_port=4242):
    """
    Listens for live telemetry from the ESP32 receiver board plugged into your USB port.
    Relays each reading to Serial Studio via UDP and logs all data to a CSV spreadsheet.
    """
    if not SERIAL_AVAILABLE:
        print("\nError: The 'pyserial' package is required for USB serial connection.")
        print("Please install it with: pip3 install pyserial\n")
        return

    print("\n" + "\033[38;5;205m" + "━" * 65 + "\033[0m")
    print("\033[38;5;218m       🌸 BPL GROUND STATION — ESP-NOW DUAL-BOARD TELEMETRY 🌸\033[0m")
    print("\033[38;5;205m" + "━" * 65 + "\033[0m")
    print(f"\033[38;5;219mSerial Port:  \033[0m{port_name} ({baud} baud)")
    print(f"\033[38;5;219mBroadcasting: \033[0mUDP 127.0.0.1:{udp_port} (Serial Studio compatible)")
    print(f"\033[38;5;219mLog Output:   \033[0m{log_path}")
    print("\033[38;5;205m" + "━" * 65 + "\033[0m")
    print("\033[38;5;213mConnecting to ESP32 receiver... (Press Ctrl+C to stop recording)\033[0m\n")

    try:
        ser = serial.Serial(port_name, baud, timeout=1.0)
    except Exception as e:
        print(f"Error opening serial port {port_name}: {e}")
        return

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    with open(log_path, "w") as f:
        f.write("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f\n")
        peak_seen = 0.0
        readings_count = 0

        try:
            while True:
                raw_line = ser.readline()
                if not raw_line:
                    continue

                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                # Echo informational messages or status lines from the board
                if line.startswith("#"):
                    print(f"\n[STAND INFO] {line}")
                    continue

                # Skip header if repeated by the board
                if "timestamp_ms" in line:
                    continue

                parts = line.split(",")
                if len(parts) >= 2:
                    try:
                        t_ms = float(parts[0])
                        thrust = float(parts[1])
                        t_casing = float(parts[2]) if len(parts) > 2 else 0.0
                        t_nozzle = float(parts[3]) if len(parts) > 3 else 0.0
                        t_ambient = float(parts[4]) if len(parts) > 4 else 0.0
                    except ValueError:
                        # Malformed line or partial packet during boot
                        continue

                    # Record to CSV
                    f.write(f"{int(t_ms)},{thrust:.2f},{t_casing:.1f},{t_nozzle:.1f},{t_ambient:.1f}\n")
                    f.flush()
                    readings_count += 1

                    # Broadcast packet over UDP for live graphing in Serial Studio
                    try:
                        udp_sock.sendto((line + "\n").encode("utf-8"), ("127.0.0.1", udp_port))
                    except Exception:
                        pass

                    if thrust > peak_seen:
                        peak_seen = thrust

                    # Live status indicator with custom pink theme
                    if thrust > 10.0:
                        state = "\033[38;5;198m\033[1m🔥 FIRING 🔥\033[0m"
                    elif t_ms > 4000:
                        state = "\033[38;5;120mSAFE / DONE\033[0m"
                    else:
                        state = "\033[38;5;218mSTAND READY\033[0m"

                    sys.stdout.write(
                        f"\r[{state}] \033[38;5;225mTime:\033[0m {t_ms/1000.0:5.2f}s | "
                        f"\033[38;5;205mForce:\033[0m \033[1m{thrust:5.1f} lbs\033[0m | "
                        f"\033[38;5;213mPeak:\033[0m {peak_seen:5.1f} lbs | "
                        f"\033[38;5;218mCasing:\033[0m {t_casing:5.1f}°F | "
                        f"\033[38;5;204mNozzle:\033[0m {t_nozzle:5.1f}°F   "
                    )
                    sys.stdout.flush()

        except KeyboardInterrupt:
            print(f"\n\nTest session stopped by user.")
        finally:
            ser.close()

    print(f"Logged {readings_count} data points to: {log_path}\n")


def run_mock_stream(log_path, motor_choice="J425R", port=4242, rate=50):
    """Generates a fake live test fire and broadcasts UDP packets locally for Serial Studio."""
    from simulator import make_fake_test_run
    
    print("\n" + "=" * 60)
    print("      BPL GROUND STATION — LIVE SIMULATION / REHEARSAL      ")
    print("=" * 60)
    print(f"Motor:        {motor_choice}")
    print(f"Broadcasting: UDP 127.0.0.1:{port} (Serial Studio compatible)")
    print(f"Log Output:   {log_path}\n")
    
    df, motor = make_fake_test_run(motor_choice=motor_choice, samples_per_sec=rate)
    
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    with open(log_path, "w") as f:
        f.write("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f\n")
        
        peak_seen = 0.0
        
        for idx, row in df.iterrows():
            t_ms = int(row["timestamp_ms"])
            thrust = row["thrust_lbf"]
            t_casing = row["temp_casing_f"]
            t_nozzle = row["temp_nozzle_f"]
            t_ambient = row["temp_ambient_f"]
            
            packet_str = f"{t_ms},{thrust:.2f},{t_casing:.1f},{t_nozzle:.1f},{t_ambient:.1f}\n"
            f.write(packet_str)
            f.flush()
            
            # Broadcast over local UDP so Serial Studio receives it live
            try:
                udp_sock.sendto(packet_str.encode("utf-8"), ("127.0.0.1", port))
            except Exception:
                pass
            
            if thrust > peak_seen:
                peak_seen = thrust
                
            # Status indicators
            if thrust > 10.0:
                state = "\033[91mFIRING\033[0m"
            elif t_ms > 4000:
                state = "\033[92mSAFE / DONE\033[0m"
            else:
                state = "\033[93mARMED / IDLE\033[0m"
                
            sys.stdout.write(f"\r[{state}] Time: {t_ms/1000.0:5.2f}s | Force: {thrust:5.1f} lbs | Peak: {peak_seen:5.1f} lbs | Casing: {t_casing:5.1f}°F | Nozzle: {t_nozzle:5.1f}°F   ")
            sys.stdout.flush()
            
            time.sleep(1.0 / rate)
            
    print("\n\nTest finished! Log file saved successfully.")

def run_replay(csv_file, port=4242, rate=50):
    """Replays an existing test CSV file over UDP into Serial Studio and terminal."""
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        return
        
    print(f"\nReplaying test file: {os.path.basename(csv_file)}")
    print(f"Broadcasting to UDP 127.0.0.1:{port} for Serial Studio...\n")
    
    df = pd.read_csv(csv_file)
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    peak_seen = 0.0
    for idx, row in df.iterrows():
        t_ms = int(row["timestamp_ms"])
        thrust = float(row["thrust_lbf"])
        t_casing = float(row.get("temp_casing_f", 72.0))
        t_nozzle = float(row.get("temp_nozzle_f", 72.0))
        t_ambient = float(row.get("temp_ambient_f", 72.0))
        
        packet_str = f"{t_ms},{thrust:.2f},{t_casing:.1f},{t_nozzle:.1f},{t_ambient:.1f}\n"
        try:
            udp_sock.sendto(packet_str.encode("utf-8"), ("127.0.0.1", port))
        except Exception:
            pass
            
        if thrust > peak_seen:
            peak_seen = thrust
            
        if thrust > 10.0:
            state = "\033[91mFIRING\033[0m"
        elif t_ms > 4000:
            state = "\033[92mSAFE / DONE\033[0m"
        else:
            state = "\033[93mARMED / IDLE\033[0m"
            
        sys.stdout.write(f"\r[{state}] Time: {t_ms/1000.0:5.2f}s | Force: {thrust:5.1f} lbs | Peak: {peak_seen:5.1f} lbs | Casing: {t_casing:5.1f}°F   ")
        sys.stdout.flush()
        time.sleep(1.0 / rate)
        
    print("\n\nReplay complete.")

def listen_wifi_udp(port, log_path):
    """Listens for real Wi-Fi packets sent by the ESP32 on test day."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))
    
    print(f"\nListening for ESP32 Wi-Fi packets on UDP port {port}...")
    print(f"Saving incoming data to: {log_path}\n")
    
    with open(log_path, "w") as f:
        f.write("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f\n")
        peak_seen = 0.0
        
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                text = data.decode("utf-8").strip()
                if not text or text.startswith("#"):
                    continue
                f.write(text + "\n")
                f.flush()
                
                parts = text.split(",")
                if len(parts) >= 2:
                    t_ms = float(parts[0])
                    thrust = float(parts[1])
                    if thrust > peak_seen:
                        peak_seen = thrust
                    sys.stdout.write(f"\r[STAND CONNECTED] Time: {t_ms/1000.0:5.2f}s | Force: {thrust:5.1f} lbs | Peak: {peak_seen:5.1f} lbs   ")
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("\nStopped recording.")

def main():
    parser = argparse.ArgumentParser(description="Live Ground Station Receiver & Replay Tool")
    parser.add_argument("--serial", nargs="?", const="auto", default=None, help="Listen to USB serial from receiver ESP32 (auto-detects port if not specified)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--wifi", action="store_true", help="Listen over Wi-Fi UDP instead of USB serial")
    parser.add_argument("--mock", action="store_true", help="Run fake test stream to test dashboard")
    parser.add_argument("--replay", type=str, default=None, help="Replay an existing CSV test log over UDP")
    parser.add_argument("--motor", type=str, default="J425R", choices=["J425R", "J435WS", "J450DM", "KNSB-38"], help="Motor to simulate in mock mode")
    parser.add_argument("--rate", type=int, default=50, help="Stream speed in readings/sec (default: 50)")
    parser.add_argument("--port", type=int, default=4242, help="UDP port (default: 4242)")
    parser.add_argument("--out", type=str, default=None, help="Output CSV path")
    args = parser.parse_args()
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    log_file = args.out or os.path.join(data_dir, f"telemetry_{now_str}.csv")
    
    if args.replay:
        run_replay(args.replay, port=args.port, rate=args.rate)
    elif args.mock:
        run_mock_stream(log_file, motor_choice=args.motor, port=args.port, rate=args.rate)
    elif args.wifi:
        listen_wifi_udp(args.port, log_file)
    else:
        # Serial mode (default if board connected, or if --serial passed)
        target_port = args.serial if (args.serial and args.serial != "auto") else find_esp32_serial_port()
        if target_port:
            listen_serial(target_port, baud=args.baud, log_path=log_file, udp_port=args.port)
        else:
            print("No ESP32 detected on USB serial ports. Falling back to Wi-Fi UDP listener...")
            listen_wifi_udp(args.port, log_file)

if __name__ == "__main__":
    main()
