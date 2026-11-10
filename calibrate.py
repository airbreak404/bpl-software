# BPL Rocket Stand - Load Cell Calibration Helper
# Author: Tyler Howard & David Insignares (Software & Electronics Subteams)
#
# What this script does:
# 1. Reads raw 24-bit numbers from the TI ADS1256 load cell ADC.
# 2. Establishes the zero-weight baseline (tare offset) while the stand is empty.
# 3. Measures the reading with a known physical weight (e.g. 25 lb cinderblock).
# 4. Computes the exact scale multiplier (counts per pound) for the ESP32 firmware.
# 5. Runs a live verification test so you can check scale accuracy before test day.

import os
import sys
import time
import argparse
import random
import statistics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_mock_reading(applied_weight_lbs=0.0):
    """Simulates raw 24-bit ADS1256 ADC counts with realistic thermal/electronic noise."""
    base_tare = 15240
    true_counts_per_lb = 33520.0
    noise = random.gauss(0, 22)
    return int(base_tare + (applied_weight_lbs * true_counts_per_lb) + noise)

def collect_samples(count=50, applied_weight=0.0, mock=False, serial_conn=None):
    """Collects N readings and returns the raw values list."""
    samples = []
    for i in range(count):
        if mock:
            val = get_mock_reading(applied_weight)
            time.sleep(0.02)
        elif serial_conn:
            line = serial_conn.readline().decode("utf-8", errors="ignore").strip()
            try:
                val = int(line.split(",")[0])
            except (ValueError, IndexError):
                continue
        else:
            val = get_mock_reading(applied_weight)
            time.sleep(0.02)
        samples.append(val)
        
        # Show progress bar
        pct = int(((i + 1) / count) * 30)
        sys.stdout.write(f"\r  Sampling: [{'=' * pct}{' ' * (30 - pct)}] {i + 1}/{count}")
        sys.stdout.flush()
    print()
    return samples

def run_calibration(mock=False, port=None, baud=115200):
    print("=" * 65)
    print("       BPL STATIC TEST STAND — LOAD CELL CALIBRATION HELPER      ")
    print("=" * 65)
    if mock:
        print(">> Running in SIMULATED (MOCK) MODE — no hardware required <<\n")
    else:
        print(f">> Connecting to ESP32 on port {port} at {baud} baud <<\n")

    print("How this works:")
    print("1. We read the empty stand to find the 'Zero Tare Offset'.")
    print("2. We place a known weight (e.g. 25 lb cinderblock) on the stand.")
    print("3. We calculate the exact counts per pound to program into the ESP32.\n")

    serial_conn = None
    if not mock and port:
        try:
            import serial
            serial_conn = serial.Serial(port, baud, timeout=2)
            time.sleep(2)
        except Exception as e:
            print(f"Error opening serial port {port}: {e}")
            print("Falling back to mock mode.\n")
            mock = True

    # -------------------------------------------------------------
    # Step 1: Zero Tare
    # -------------------------------------------------------------
    print("-------------------------------------------------------------")
    print("STEP 1: Zero Weight Calibration (Empty Stand)")
    print("-------------------------------------------------------------")
    print("Make sure the test stand is completely empty with NO motor or weights.")
    input("Press [Enter] when the stand is resting still to record baseline...")
    
    zero_samples = collect_samples(count=60, applied_weight=0.0, mock=mock, serial_conn=serial_conn)
    zero_avg = statistics.mean(zero_samples)
    zero_std = statistics.stdev(zero_samples) if len(zero_samples) > 1 else 0.0
    
    print(f"  -> Average Zero Offset: {zero_avg:.1f} ADC counts")
    print(f"  -> Noise Floor (StdDev): ±{zero_std:.1f} counts (clean signal)\n")

    # -------------------------------------------------------------
    # Step 2: Test Weight
    # -------------------------------------------------------------
    print("-------------------------------------------------------------")
    print("STEP 2: Known Weight Calibration")
    print("-------------------------------------------------------------")
    weight_input = input("Enter known test weight in pounds [default: 25.0]: ").strip()
    known_weight = float(weight_input) if weight_input else 25.0

    print(f"Carefully place your {known_weight:.1f} lb test weight on the load cell plate.")
    input("Press [Enter] once the weight is steady...")
    
    loaded_samples = collect_samples(count=60, applied_weight=known_weight, mock=mock, serial_conn=serial_conn)
    loaded_avg = statistics.mean(loaded_samples)
    loaded_std = statistics.stdev(loaded_samples) if len(loaded_samples) > 1 else 0.0
    
    print(f"  -> Average Loaded Reading: {loaded_avg:.1f} ADC counts")
    print(f"  -> Noise Floor with Load:  ±{loaded_std:.1f} counts\n")

    # -------------------------------------------------------------
    # Step 3: Math & Scaling Factor
    # -------------------------------------------------------------
    delta = loaded_avg - zero_avg
    if delta <= 0:
        print("[!] ERROR: Loaded reading was not higher than zero reading!")
        print("    Check load cell wiring polarity (SIG+ vs SIG-).\n")
        return

    counts_per_lbf = delta / known_weight

    print("=" * 65)
    print("                    CALIBRATION RESULTS                          ")
    print("=" * 65)
    print(f"Zero Tare Offset:       {zero_avg:12.1f} counts")
    print(f"Delta with {known_weight} lbs:    {delta:12.1f} counts")
    print(f"Scale Factor:           {counts_per_lbf:12.1f} counts per pound (lbf)")
    print(f"Theoretical Resolution: {1.0 / counts_per_lbf:12.5f} lbs per count (ultra-fine)")
    print("=" * 65)

    print("\nCopy & paste these exact two lines into firmware/bpl_test_stand_esp32.ino:")
    print("-" * 65)
    print(f"float calibration_counts_per_lbf = {counts_per_lbf:.1f};")
    print(f"float zero_tare_offset = {zero_avg:.1f};")
    print("-" * 65 + "\n")

    # -------------------------------------------------------------
    # Step 4: Real-Time Verification
    # -------------------------------------------------------------
    print("Live scale verification test (press Ctrl+C to exit):")
    print("Try removing the weight, pushing gently, or testing different items.")
    print("Target reading right now should be approx:", f"{known_weight:.1f} lbs\n")

    try:
        applied = known_weight
        for step in range(25):
            time.sleep(0.2)
            if mock and step > 10 and step <= 15:
                applied = 0.0 # simulate taking the weight off
            elif mock and step > 15:
                applied = 12.5 # simulate half weight
                
            raw = get_mock_reading(applied) if mock else (
                int(serial_conn.readline().decode().strip().split(",")[0]) if serial_conn else 0
            )
            lbs = (raw - zero_avg) / counts_per_lbf
            if lbs < 0.05:
                lbs = 0.0
            sys.stdout.write(f"\r[SCALE LIVE] Raw: {raw:8d} | Measured Weight: {lbs:6.2f} lbs   ")
            sys.stdout.flush()
        print("\n\nScale verification completed successfully.")
    except KeyboardInterrupt:
        print("\n\nExited calibration verification.")

def main():
    parser = argparse.ArgumentParser(description="BPL Static Stand Load Cell Calibration Tool")
    parser.add_argument("--mock", action="store_true", help="Run simulated calibration without physical stand")
    parser.add_argument("--port", type=str, default=None, help="Serial port (e.g. /dev/cu.usbserial-*)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    args = parser.parse_args()

    # Default to mock mode if no serial port is specified
    is_mock = args.mock or (args.port is None)
    run_calibration(mock=is_mock, port=args.port, baud=args.baud)

if __name__ == "__main__":
    main()
