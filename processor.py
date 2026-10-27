# BPL Rocket Stand - Test Data Processor
# Takes the raw numbers from a test fire, zeroes out the scale, finds the burn time, and draws clean charts.
# Author: Tyler Howard (Software Subteam)

import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1 pound of force = 4.44822 Newtons
LBF_TO_NEWTONS = 4.4482216

# Standard rocketry motor letter sizes based on total impulse (in Newton-seconds)
MOTOR_CLASSES = [
    ("A", 1.26, 2.5),
    ("B", 2.51, 5.0),
    ("C", 5.01, 10.0),
    ("D", 10.01, 20.0),
    ("E", 20.01, 40.0),
    ("F", 40.01, 80.0),
    ("G", 80.01, 160.0),
    ("H", 160.01, 320.0),
    ("I", 320.01, 640.0),
    ("J", 640.01, 1280.0),
    ("K", 1280.01, 2560.0),
    ("L", 2560.01, 5120.0),
    ("M", 5120.01, 10240.0),
]

def find_motor_letter(impulse_ns):
    for letter, low, high in MOTOR_CLASSES:
        if low <= impulse_ns <= high:
            pct = ((impulse_ns - low) / (high - low)) * 100
            return f"{letter} (approx {pct:.0f}% into class)"
    if impulse_ns < 1.26:
        return "< A class"
    return "> M class"

def run_analysis(csv_file, save_folder=None):
    if not os.path.exists(csv_file):
        print(f"Cannot find file: {csv_file}")
        return None
        
    print(f"\nAnalyzing test file: {os.path.basename(csv_file)}")
    
    df = pd.read_csv(csv_file)
    if "timestamp_ms" not in df.columns or "thrust_lbf" not in df.columns:
        print("Missing required columns (timestamp_ms, thrust_lbf).")
        return None
        
    # Convert milliseconds to seconds
    df["time_sec"] = (df["timestamp_ms"] - df["timestamp_ms"].iloc[0]) / 1000.0
    
    # Calculate sample speed
    dt = df["time_sec"].diff().median()
    hz = (1.0 / dt) if dt > 0 else 0
    print(f"Data points: {len(df):,} | Sampling speed: {hz:.0f} readings/sec | Total log time: {df['time_sec'].iloc[-1]:.2f}s")
    
    # 1. Zero out the scale (tare)
    # Grab the first half second while the motor is just sitting there waiting to fire
    idle_points = df[df["time_sec"] < 0.5]
    tare_offset = idle_points["thrust_lbf"].median() if len(idle_points) > 5 else 0.0
    df["clean_thrust_lbf"] = (df["thrust_lbf"] - tare_offset).clip(lower=0.0)
    
    # Smooth out electronic noise with a quick rolling average
    df["smooth_thrust_lbf"] = df["clean_thrust_lbf"].rolling(window=5, min_periods=1, center=True).mean()
    
    # 2. Find when the motor actually burned
    peak_force = df["smooth_thrust_lbf"].max()
    threshold = 0.05 * peak_force  # 5% of peak marks start and end of fire
    
    burn_pts = df[df["smooth_thrust_lbf"] >= threshold]
    if len(burn_pts) < 5:
        print("Could not find a clear motor firing in this data file.")
        return None
        
    t_start = burn_pts["time_sec"].iloc[0]
    t_end = burn_pts["time_sec"].iloc[-1]
    burn_time = t_end - t_start
    
    # Data during just the burn
    burn_df = df[(df["time_sec"] >= t_start) & (df["time_sec"] <= t_end)].copy()
    
    # 3. Calculate numbers
    peak_newtons = peak_force * LBF_TO_NEWTONS
    avg_force = burn_df["clean_thrust_lbf"].mean()
    avg_newtons = avg_force * LBF_TO_NEWTONS
    
    # Total impulse = sum of (force * time slice) in Newtons
    burn_newtons = burn_df["clean_thrust_lbf"] * LBF_TO_NEWTONS
    total_impulse = float(np.trapezoid(burn_newtons.values, burn_df["time_sec"].values))
    motor_class = find_motor_letter(total_impulse)
    
    # Cumulative push over time
    df["thrust_newtons"] = df["clean_thrust_lbf"] * LBF_TO_NEWTONS
    df["running_impulse"] = np.cumsum(df["thrust_newtons"] * dt)
    
    has_temp = "temp_casing_f" in df.columns and "temp_nozzle_f" in df.columns
    
    # Print clean results
    print("\n" + "=" * 50)
    print("              TEST RESULTS SUMMARY               ")
    print("=" * 50)
    print(f"Burn Time:         {burn_time:.3f} seconds (from {t_start:.2f}s to {t_end:.2f}s)")
    print(f"Max Push (Peak):   {peak_force:.2f} lbs ({peak_newtons:.1f} Newtons)")
    print(f"Average Push:      {avg_force:.2f} lbs ({avg_newtons:.1f} Newtons)")
    print(f"Total Impulse:     {total_impulse:.1f} N-sec (total energy delivered)")
    print(f"Motor Class:       {motor_class}")
    if has_temp:
        print(f"Max Casing Temp:   {df['temp_casing_f'].max():.1f} °F")
        print(f"Max Nozzle Temp:   {df['temp_nozzle_f'].max():.1f} °F")
    print("=" * 50 + "\n")
    
    # 4. Draw plots
    fig, axes = plt.subplots(3 if has_temp else 2, 1, figsize=(10, 8 if has_temp else 6), sharex=True)
    
    # Plot 1: Force vs Time
    ax1 = axes[0]
    ax1.plot(df["time_sec"], df["clean_thrust_lbf"], color="#90caf9", label="Raw Sensor", alpha=0.6, linewidth=1)
    ax1.plot(df["time_sec"], df["smooth_thrust_lbf"], color="#0d47a1", label="Filtered Curve", linewidth=2)
    ax1.fill_between(burn_df["time_sec"], burn_df["smooth_thrust_lbf"], color="#1976d2", alpha=0.2, label="Burn Window")
    
    # Peak marker
    peak_idx = df["smooth_thrust_lbf"].idxmax()
    peak_t = df["time_sec"].iloc[peak_idx]
    ax1.annotate(f"Peak: {peak_force:.1f} lbs ({peak_newtons:.0f} N)",
                 xy=(peak_t, peak_force),
                 xytext=(peak_t + 0.3, peak_force * 0.88),
                 arrowprops=dict(facecolor="black", shrink=0.05, width=1.2, headwidth=6),
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff3e0", edgecolor="#ff9800"),
                 fontweight="bold", fontsize=10)
                 
    ax1.axvline(t_start, color="green", linestyle="--", alpha=0.8, label=f"Ignition ({t_start:.2f}s)")
    ax1.axvline(t_end, color="red", linestyle="--", alpha=0.8, label=f"Burnout ({t_end:.2f}s)")
    ax1.set_ylabel("Thrust (lbs)", fontsize=11)
    ax1.set_title(f"BPL Static Fire Test — {os.path.basename(csv_file)}", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right")
    
    # Plot 2: Total Push (Cumulative Impulse)
    ax2 = axes[1]
    ax2.plot(df["time_sec"], df["running_impulse"], color="#e65100", linewidth=2, label="Total Energy (N-sec)")
    ax2.axhline(total_impulse, color="#bf360c", linestyle=":", label=f"Final Total: {total_impulse:.1f} N-sec")
    ax2.set_ylabel("Impulse (N-sec)", fontsize=11)
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="lower right")
    
    # Plot 3: Temperatures
    if has_temp:
        ax3 = axes[2]
        ax3.plot(df["time_sec"], df["temp_nozzle_f"], color="#c62828", label="Nozzle", linewidth=2)
        ax3.plot(df["time_sec"], df["temp_casing_f"], color="#ef6c00", label="Casing", linewidth=2)
        ax3.plot(df["time_sec"], df["temp_ambient_f"], color="#757575", linestyle="--", label="Ambient", alpha=0.7)
        ax3.set_ylabel("Temp (°F)", fontsize=11)
        ax3.set_xlabel("Time (seconds)", fontsize=11)
        ax3.grid(True, linestyle=":", alpha=0.6)
        ax3.legend(loc="upper left")
    else:
        ax2.set_xlabel("Time (seconds)", fontsize=11)
        
    plt.tight_layout()
    
    # Save graph
    out_dir = save_folder or "/Users/thoward/Documents/AIAA/BPL_Software/reports"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(csv_file))[0]
    out_img = os.path.join(out_dir, f"{base}_report.png")
    plt.savefig(out_img, dpi=300)
    plt.close()
    
    print(f"Saved chart to: {out_img}")
    return out_img

def main():
    parser = argparse.ArgumentParser(description="Process test stand CSV files")
    parser.add_argument("file", nargs="?", help="CSV file to process (defaults to newest in data/)")
    args = parser.parse_args()
    
    if args.file:
        target = args.file
    else:
        files = glob.glob("/Users/thoward/Documents/AIAA/BPL_Software/data/*.csv")
        if not files:
            print("No CSV files found in data/. Run simulator.py first.")
            return
        target = max(files, key=os.path.getctime)
        
    run_analysis(target)

if __name__ == "__main__":
    main()
