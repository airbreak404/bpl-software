# BPL Rocket Stand - Test Data Simulator
# Generates fake test fire numbers so we can test our software without blowing up actual rocket motors.

import os
import argparse
import random
import math
import pandas as pd
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Standard motor specs from the manufacturer spec sheets
MOTOR_SPECS = {
    "J425R": {
        "name": "Aerotech J425R-14A",
        "burn_time": 1.6,
        "peak_force": 102.0,
        "propellant": "Redline",
        "casing_max_temp": 260.0,
        "nozzle_max_temp": 410.0,
    },
    "J435WS": {
        "name": "Aerotech J435WS DMS",
        "burn_time": 1.7,
        "peak_force": 156.5,
        "propellant": "White Lightning",
        "casing_max_temp": 290.0,
        "nozzle_max_temp": 460.0,
    },
    "J450DM": {
        "name": "Aerotech J450DM-14A",
        "burn_time": 2.4,
        "peak_force": 125.0,
        "propellant": "Dark Matter",
        "casing_max_temp": 320.0,
        "nozzle_max_temp": 480.0,
    },
    "KNSB-38": {
        "name": "BPL 38mm KNSB (Homemade Sugar Motor)",
        "burn_time": 1.0,
        "peak_force": 85.0,
        "propellant": "Potassium Nitrate + Sorbitol",
        "casing_max_temp": 220.0,
        "nozzle_max_temp": 390.0,
    }
}

def make_fake_test_run(motor_choice="J425R", samples_per_sec=200, pre_fire_sec=2.0, post_fire_sec=3.0):
    motor = MOTOR_SPECS.get(motor_choice, MOTOR_SPECS["J425R"])
    burn = motor["burn_time"]
    total_time = pre_fire_sec + burn + post_fire_sec
    
    total_samples = int(total_time * samples_per_sec)
    dt = 1.0 / samples_per_sec
    
    times = []
    forces = []
    casing_temps = []
    nozzle_temps = []
    ambient_temps = []
    
    outside_temp = 72.0
    c_temp = outside_temp
    n_temp = outside_temp
    peak = motor["peak_force"]
    
    for i in range(total_samples):
        t = i * dt
        t_ms = int(t * 1000)
        times.append(t_ms)
        
        # Idle baseline reading (motor sitting still on the scale with slight sensor wobble)
        current_force = 0.2 + random.gauss(0, 0.12)
        
        # During the burn
        if pre_fire_sec <= t < (pre_fire_sec + burn):
            progress = (t - pre_fire_sec) / burn
            
            # Rocket motor thrust profile: quick spike at start, steady burn, then drops off
            if progress < 0.12:
                # Ignition spike
                curve = math.sin((progress / 0.12) * (math.pi / 2))
                thrust = peak * curve
            elif progress < 0.85:
                # Steady burn
                decay = 1.0 - 0.25 * ((progress - 0.12) / 0.73)
                thrust = (peak * 0.82) * decay
            else:
                # Burnout tail-off
                tail = (progress - 0.85) / 0.15
                thrust = (peak * 0.6) * (1.0 - tail)**2
                
            # Add combustion flutter
            noise = random.gauss(0, peak * 0.02)
            current_force += max(0.0, thrust + noise)
            
            # Heat up thermocouples
            c_temp += (motor["casing_max_temp"] - c_temp) * (dt * 1.8)
            n_temp += (motor["nozzle_max_temp"] - n_temp) * (dt * 3.5)
            
        elif t >= (pre_fire_sec + burn):
            # After fire: slowly cools back down
            c_temp += (outside_temp - c_temp) * (dt * 0.05)
            n_temp += (outside_temp - n_temp) * (dt * 0.08)
            
        forces.append(round(current_force, 3))
        casing_temps.append(round(c_temp + random.gauss(0, 0.2), 2))
        nozzle_temps.append(round(n_temp + random.gauss(0, 0.3), 2))
        ambient_temps.append(round(outside_temp + random.gauss(0, 0.1), 2))
        
    df = pd.DataFrame({
        "timestamp_ms": times,
        "thrust_lbf": forces,
        "temp_casing_f": casing_temps,
        "temp_nozzle_f": nozzle_temps,
        "temp_ambient_f": ambient_temps
    })
    
    return df, motor

def main():
    parser = argparse.ArgumentParser(description="Generate fake test fire data for the BPL stand")
    parser.add_argument("--motor", choices=["J425R", "J435WS", "J450DM", "KNSB-38"], default="J425R", help="Motor to simulate")
    parser.add_argument("--rate", type=int, default=200, help="Samples per second (default: 200)")
    parser.add_argument("--out", type=str, default=None, help="Where to save the CSV")
    args = parser.parse_args()
    
    print(f"Generating fake test data for {args.motor}...")
    df, motor = make_fake_test_run(motor_choice=args.motor, samples_per_sec=args.rate)
    
    if args.out:
        out_path = args.out
    else:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        out_path = os.path.join(data_dir, f"simulated_{args.motor}_{now_str}.csv")
        
    df.to_csv(out_path, index=False)
    print(f"Done! Saved {len(df)} rows to: {out_path}")
    print(f"Motor: {motor['name']} | Expected Burn: {motor['burn_time']}s | Expected Peak: {motor['peak_force']} lbs")

if __name__ == "__main__":
    main()
