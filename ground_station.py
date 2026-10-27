# BPL Ground Station & Live Telemetry Monitor
# Listens for sensor readings from the test stand over USB or Wi-Fi and logs everything to a CSV.
# Author: Tyler Howard & Sofia Martinez (Software Subteam)

import sys
import os
import time
import argparse
import socket
from datetime import datetime

def run_mock_stream(log_path, rate=50):
    """Generates a fake live test fire right on your laptop so you can test the UI."""
    from simulator import make_fake_test_run
    
    print("\nRunning in MOCK MODE (Simulated Stand)")
    print(f"Logging data to: {log_path}\n")
    
    df, motor = make_fake_test_run(motor_choice="J425R", samples_per_sec=rate)
    
    with open(log_path, "w") as f:
        f.write("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f\n")
        
        peak_seen = 0.0
        
        for idx, row in df.iterrows():
            t_ms = int(row["timestamp_ms"])
            thrust = row["thrust_lbf"]
            t_casing = row["temp_casing_f"]
            t_nozzle = row["temp_nozzle_f"]
            t_ambient = row["temp_ambient_f"]
            
            f.write(f"{t_ms},{thrust},{t_casing},{t_nozzle},{t_ambient}\n")
            f.flush()
            
            if thrust > peak_seen:
                peak_seen = thrust
                
            # Quick status indicators
            if thrust > 10.0:
                state = "\033[91mFIRING\033[0m"
            elif t_ms > 4000:
                state = "\033[92mSAFE / DONE\033[0m"
            else:
                state = "\033[93mARMED / IDLE\033[0m"
                
            sys.stdout.write(f"\r[{state}] Time: {t_ms/1000.0:5.2f}s | Force: {thrust:5.1f} lbs | Peak: {peak_seen:5.1f} lbs | Casing: {t_casing:5.1f}°F | Nozzle: {t_nozzle:5.1f}°F")
            sys.stdout.flush()
            
            time.sleep(1.0 / rate)
            
    print("\n\nTest finished! Log file saved successfully.")

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
                    sys.stdout.write(f"\r[STAND CONNECTED] Time: {t_ms/1000.0:5.2f}s | Force: {thrust:5.1f} lbs | Peak: {peak_seen:5.1f} lbs")
                    sys.stdout.flush()
        except KeyboardInterrupt:
            print("\nStopped recording.")

def main():
    parser = argparse.ArgumentParser(description="Live Ground Station Receiver")
    parser.add_argument("--mock", action="store_true", help="Run fake test stream to test dashboard")
    parser.add_argument("--port", type=int, default=4242, help="UDP port (default: 4242)")
    parser.add_argument("--out", type=str, default=None, help="Output CSV path")
    args = parser.parse_args()
    
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = args.out or f"/Users/thoward/Documents/AIAA/BPL_Software/data/telemetry_{now_str}.csv"
    
    if args.mock:
        run_mock_stream(log_file)
    else:
        listen_wifi_udp(args.port, log_file)

if __name__ == "__main__":
    main()
