# BPL Rocket Stand - Test Data Processor
# Author: Tyler Howard (Software Subteam)
#
# What this script does:
# 1. Reads a CSV test file from the rocket stand (or simulator).
# 2. Tares (zeroes) the scale so we don't accidentally measure the motor's resting weight.
# 3. Finds exactly when the rocket ignited and when it burned out.
# 4. Calculates peak force, average force, burn duration, and total energy (total impulse).
# 5. Generates a clean chart PNG and a formatted summary Excel workbook.

import os
import glob
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1 pound of force (lbf) = 4.44822 Newtons (N)
LBF_TO_NEWTONS = 4.4482216

# Certified manufacturer motor specifications (from AeroTech / ThrustCurve.org)
CERTIFIED_SPECS = {
    "J425R": {
        "name": "Aerotech J425R-14A (Redline)",
        "burn_time": 1.6,
        "peak_force_lbf": 102.0,
        "avg_force_lbf": 66.8,
        "total_impulse_ns": 457.0,
        "motor_class": "J",
    },
    "J435WS": {
        "name": "Aerotech J435WS DMS (White Lightning)",
        "burn_time": 1.7,
        "peak_force_lbf": 156.5,
        "avg_force_lbf": 102.4,
        "total_impulse_ns": 774.0,
        "motor_class": "J",
    },
    "J450DM": {
        "name": "Aerotech J450DM-14A (Dark Matter)",
        "burn_time": 2.4,
        "peak_force_lbf": 125.0,
        "avg_force_lbf": 95.0,
        "total_impulse_ns": 1098.0,
        "motor_class": "J",
    },
    "KNSB-38": {
        "name": "BPL 38mm KNSB (Sugar Motor)",
        "burn_time": 1.0,
        "peak_force_lbf": 85.0,
        "avg_force_lbf": 55.0,
        "total_impulse_ns": 245.0,
        "motor_class": "H",
    }
}

# Standard rocket motor letter classes (A through M) based on total impulse in Newton-seconds.
# In rocketry, every letter has double the total push energy of the letter before it.
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
    """
    Takes total impulse in Newton-seconds and returns which letter class it belongs to
    (e.g. 'I class (approx 43% into class)').
    """
    for letter, low, high in MOTOR_CLASSES:
        if low <= impulse_ns <= high:
            pct = ((impulse_ns - low) / (high - low)) * 100
            return f"{letter} (approx {pct:.0f}% into class)"
    if impulse_ns < 1.26:
        return "< A class"
    return "> M class"

def run_analysis(csv_file, save_folder=None, motor_choice=None):
    if not os.path.exists(csv_file):
        print(f"Error: Cannot find file '{csv_file}'")
        return None
        
    print(f"\nAnalyzing test file: {os.path.basename(csv_file)}")
    
    # Identify target motor spec for comparison
    detected_motor = motor_choice
    if not detected_motor:
        for m in CERTIFIED_SPECS.keys():
            if m in os.path.basename(csv_file):
                detected_motor = m
                break
    spec = CERTIFIED_SPECS.get(detected_motor)
    
    # Read the raw CSV file into a table
    df = pd.read_csv(csv_file)
    if "timestamp_ms" not in df.columns or "thrust_lbf" not in df.columns:
        print("Error: Missing required columns (timestamp_ms, thrust_lbf).")
        return None
        
    # Convert timestamps from milliseconds to seconds starting at 0.0s
    df["time_sec"] = (df["timestamp_ms"] - df["timestamp_ms"].iloc[0]) / 1000.0
    
    # Check how fast the sensor was recording (sampling rate)
    dt = df["time_sec"].diff().median()
    hz = (1.0 / dt) if dt > 0 else 0
    print(f"Data points: {len(df):,} | Sampling speed: {hz:.0f} readings/sec | Total log time: {df['time_sec'].iloc[-1]:.2f}s")
    
    # -------------------------------------------------------------
    # Step 1: Zero out the scale (Tare)
    # Just like hitting "tare" on a kitchen scale before pouring sugar.
    # We take the median of the first half-second while the rocket is just sitting
    # there cold on the stand, and subtract that baseline weight from every reading.
    # -------------------------------------------------------------
    idle_points = df[df["time_sec"] < 0.5]
    tare_offset = idle_points["thrust_lbf"].median() if len(idle_points) > 5 else 0.0
    df["clean_thrust_lbf"] = (df["thrust_lbf"] - tare_offset).clip(lower=0.0)
    
    # Smooth out tiny electronic sensor wiggles using a 5-point rolling average
    df["smooth_thrust_lbf"] = df["clean_thrust_lbf"].rolling(window=5, min_periods=1, center=True).mean()
    
    # -------------------------------------------------------------
    # Step 2: Find when the rocket actually lit and when it went out
    # We find the peak force, then set a 5% threshold. Anything above 5% of peak
    # is considered part of the real motor burn. This cleanly ignores any tiny bumps
    # before ignition and cuts off right when the flame dies down.
    # -------------------------------------------------------------
    peak_force = df["smooth_thrust_lbf"].max()
    threshold = 0.05 * peak_force  
    
    burn_pts = df[df["smooth_thrust_lbf"] >= threshold]
    if len(burn_pts) < 5:
        print("Warning: Could not find a clear motor firing in this data file.")
        return None
        
    t_start = burn_pts["time_sec"].iloc[0]
    t_end = burn_pts["time_sec"].iloc[-1]
    burn_time = t_end - t_start
    
    # Subset of data during just the active firing
    burn_df = df[(df["time_sec"] >= t_start) & (df["time_sec"] <= t_end)].copy()
    
    # -------------------------------------------------------------
    # Step 3: Calculate the numbers everyone asks for
    # -------------------------------------------------------------
    peak_newtons = peak_force * LBF_TO_NEWTONS
    avg_force = burn_df["clean_thrust_lbf"].mean()
    avg_newtons = avg_force * LBF_TO_NEWTONS
    
    # Total Impulse: This is the total "push energy" the motor produced.
    # Rocket scientists call this the "area under the curve". In code, it literally
    # just means multiplying each little slice of force by the time slice (dt)
    # and adding them all together using the trapezoid rule.
    burn_newtons = burn_df["clean_thrust_lbf"] * LBF_TO_NEWTONS
    total_impulse = float(np.trapezoid(burn_newtons.values, burn_df["time_sec"].values))
    motor_class = find_motor_letter(total_impulse)
    
    # Running cumulative push across the whole test (for the middle graph)
    df["thrust_newtons"] = df["clean_thrust_lbf"] * LBF_TO_NEWTONS
    df["running_impulse"] = np.cumsum(df["thrust_newtons"] * dt)
    
    # Temperature check (if thermocouples were hooked up during this test)
    has_temp = "temp_casing_f" in df.columns and "temp_nozzle_f" in df.columns
    max_casing = df["temp_casing_f"].max() if has_temp else 0.0
    max_nozzle = df["temp_nozzle_f"].max() if has_temp else 0.0
    
    # Print clean results to the terminal
    print("\n" + "=" * 50)
    print("              TEST RESULTS SUMMARY               ")
    print("=" * 50)
    print(f"Burn Time:         {burn_time:.3f} seconds (from {t_start:.2f}s to {t_end:.2f}s)")
    print(f"Max Push (Peak):   {peak_force:.2f} lbs ({peak_newtons:.1f} Newtons)")
    print(f"Average Push:      {avg_force:.2f} lbs ({avg_newtons:.1f} Newtons)")
    print(f"Total Impulse:     {total_impulse:.1f} N-sec (total energy delivered)")
    print(f"Motor Class:       {motor_class}")
    if has_temp:
        print(f"Max Casing Temp:   {max_casing:.1f} °F")
        print(f"Max Nozzle Temp:   {max_nozzle:.1f} °F")
        
    p_err = t_err = i_err = 0.0
    if spec:
        p_err = ((peak_force - spec["peak_force_lbf"]) / spec["peak_force_lbf"]) * 100.0
        i_err = ((total_impulse - spec["total_impulse_ns"]) / spec["total_impulse_ns"]) * 100.0
        t_err = ((burn_time - spec["burn_time"]) / spec["burn_time"]) * 100.0
        print("-" * 50)
        print(f"      MANUFACTURER SPEC COMPARISON ({detected_motor})")
        print("-" * 50)
        print(f"Peak Force:    Measured {peak_force:6.2f} lbs | Spec {spec['peak_force_lbf']:6.2f} lbs ({p_err:+.1f}%)")
        print(f"Burn Time:     Measured {burn_time:6.3f} s   | Spec {spec['burn_time']:6.3f} s   ({t_err:+.1f}%)")
        print(f"Total Impulse: Measured {total_impulse:6.1f} N·s | Spec {spec['total_impulse_ns']:6.1f} N·s ({i_err:+.1f}%)")
    print("=" * 50 + "\n")
    
    # -------------------------------------------------------------
    # Step 4: Plot the graphs (Styled with sleek dark/pink theme)
    # -------------------------------------------------------------
    plt.style.use("dark_background")
    fig, axes = plt.subplots(3 if has_temp else 2, 1, figsize=(11, 8.5 if has_temp else 6.5), sharex=True)
    
    # Palette definition (Cosmic Pink / Synthwave Aero)
    bg_dark = "#13111c"
    card_dark = "#1c1829"
    grid_color = "#322947"
    pink_hot = "#ff2a85"
    pink_soft = "#f472b6"
    pink_glow = "#fbcfe8"
    purple_accent = "#c084fc"
    magenta_accent = "#e879f9"
    coral_pink = "#fb7185"
    text_light = "#fdf2f8"
    
    fig.patch.set_facecolor(bg_dark)
    
    for ax in axes:
        ax.set_facecolor(card_dark)
        ax.grid(True, linestyle="--", linewidth=0.6, color=grid_color, alpha=0.7)
        for spine in ax.spines.values():
            spine.set_color(grid_color)
            spine.set_linewidth(1.0)
        ax.tick_params(colors="#cbd5e1", labelsize=9)
    
    # Top Plot: Force vs Time
    ax1 = axes[0]
    ax1.plot(df["time_sec"], df["clean_thrust_lbf"], color=pink_soft, label="Raw Sensor Readings", alpha=0.35, linewidth=1.0)
    ax1.plot(df["time_sec"], df["smooth_thrust_lbf"], color=pink_hot, label="Filtered Thrust Curve", linewidth=2.4)
    ax1.fill_between(burn_df["time_sec"], burn_df["smooth_thrust_lbf"], color=pink_hot, alpha=0.22, label="Active Burn Window")
    
    # Peak Force Callout Box
    peak_idx = df["smooth_thrust_lbf"].idxmax()
    peak_t = df["time_sec"].iloc[peak_idx]
    ax1.annotate(f"★ Peak: {peak_force:.1f} lbs ({peak_newtons:.0f} N)",
                 xy=(peak_t, peak_force),
                 xytext=(peak_t + 0.35, peak_force * 0.90),
                 arrowprops=dict(facecolor=pink_hot, edgecolor=pink_glow, shrink=0.08, width=1.5, headwidth=6),
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#2b1a38", edgecolor=pink_hot, linewidth=1.5),
                 fontweight="bold", fontsize=10, color=text_light)
                 
    ax1.axvline(t_start, color=purple_accent, linestyle="--", alpha=0.85, linewidth=1.4, label=f"Ignition ({t_start:.2f}s)")
    ax1.axvline(t_end, color=coral_pink, linestyle="--", alpha=0.85, linewidth=1.4, label=f"Burnout ({t_end:.2f}s)")
    if spec:
        ax1.axhline(spec["peak_force_lbf"], color="#f43f5e", linestyle=":", linewidth=1.6, alpha=0.9,
                    label=f"Certified Target ({spec['peak_force_lbf']:.1f} lbs)")
    ax1.set_ylabel("Thrust (lbs)", fontsize=11, fontweight="bold", color=text_light)
    ax1.set_title(f"BPL Static Fire Telemetry Analysis — {os.path.basename(csv_file)}", 
                  fontsize=13, fontweight="bold", pad=12, color=pink_glow)
    legend1 = ax1.legend(loc="upper right", framealpha=0.8, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend1.get_texts(), color=text_light)
    
    # Middle Plot: Cumulative Impulse
    ax2 = axes[1]
    ax2.plot(df["time_sec"], df["running_impulse"], color=magenta_accent, linewidth=2.2, label="Cumulative Energy (N·s)")
    ax2.fill_between(df["time_sec"], df["running_impulse"], color=magenta_accent, alpha=0.15)
    ax2.axhline(total_impulse, color=purple_accent, linestyle=":", linewidth=1.5, label=f"Final Impulse: {total_impulse:.1f} N·s ({motor_class})")
    ax2.set_ylabel("Impulse (N·s)", fontsize=11, fontweight="bold", color=text_light)
    legend2 = ax2.legend(loc="lower right", framealpha=0.8, facecolor=card_dark, edgecolor=grid_color)
    plt.setp(legend2.get_texts(), color=text_light)
    
    # Bottom Plot: Heating curves
    if has_temp:
        ax3 = axes[2]
        ax3.plot(df["time_sec"], df["temp_nozzle_f"], color=pink_hot, label=f"Nozzle (Max {max_nozzle:.1f}°F)", linewidth=2.2)
        ax3.plot(df["time_sec"], df["temp_casing_f"], color=coral_pink, label=f"Casing (Max {max_casing:.1f}°F)", linewidth=2.0)
        ax3.plot(df["time_sec"], df["temp_ambient_f"], color="#94a3b8", linestyle="--", label="Ambient", alpha=0.7)
        ax3.set_ylabel("Temp (°F)", fontsize=11, fontweight="bold", color=text_light)
        ax3.set_xlabel("Time (seconds)", fontsize=11, fontweight="bold", color=text_light)
        legend3 = ax3.legend(loc="upper left", framealpha=0.8, facecolor=card_dark, edgecolor=grid_color)
        plt.setp(legend3.get_texts(), color=text_light)
    else:
        ax2.set_xlabel("Time (seconds)", fontsize=11, fontweight="bold", color=text_light)
        
    plt.tight_layout()
    
    # Save the chart PNG
    out_dir = save_folder or os.path.join(BASE_DIR, "reports")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(csv_file))[0]
    out_img = os.path.join(out_dir, f"{base}_report.png")
    plt.savefig(out_img, dpi=300)
    plt.close()
    print(f"Saved chart to: {out_img}")
    
    # -------------------------------------------------------------
    # Step 5: Export formatted Excel workbook (.xlsx)
    # -------------------------------------------------------------
    out_excel = os.path.join(out_dir, f"{base}_summary.xlsx")
    summary_data = {
        "Metric": [
            "Test File",
            "Burn Time (s)",
            "Ignition Time (s)",
            "Burnout Time (s)",
            "Peak Thrust (lbf)",
            "Peak Thrust (N)",
            "Average Thrust (lbf)",
            "Average Thrust (N)",
            "Total Impulse (N·s)",
            "Motor Classification",
            "Max Casing Temp (°F)",
            "Max Nozzle Temp (°F)",
            "Sampling Rate (Hz)"
        ],
        "Value": [
            os.path.basename(csv_file),
            round(burn_time, 3),
            round(t_start, 2),
            round(t_end, 2),
            round(peak_force, 2),
            round(peak_newtons, 1),
            round(avg_force, 2),
            round(avg_newtons, 1),
            round(total_impulse, 1),
            motor_class,
            round(max_casing, 1) if has_temp else "N/A",
            round(max_nozzle, 1) if has_temp else "N/A",
            round(hz, 0)
        ]
    }
    if spec:
        summary_data["Metric"].extend([
            "Certified Spec Target",
            "Spec Peak Thrust (lbf)",
            "Peak Thrust Error (%)",
            "Spec Burn Time (s)",
            "Burn Time Error (%)",
            "Spec Total Impulse (N·s)",
            "Total Impulse Error (%)"
        ])
        summary_data["Value"].extend([
            spec["name"],
            spec["peak_force_lbf"],
            f"{p_err:+.1f}%",
            spec["burn_time"],
            f"{t_err:+.1f}%",
            spec["total_impulse_ns"],
            f"{i_err:+.1f}%"
        ])

    summary_df = pd.DataFrame(summary_data)
    
    export_cols = ["time_sec", "clean_thrust_lbf", "smooth_thrust_lbf", "thrust_newtons", "running_impulse"]
    if has_temp:
        export_cols.extend(["temp_casing_f", "temp_nozzle_f", "temp_ambient_f"])
        
    time_df = df[export_cols].copy()
    time_df = time_df.rename(columns={
        "time_sec": "Time (s)",
        "clean_thrust_lbf": "Thrust (lbf)",
        "smooth_thrust_lbf": "Filtered Thrust (lbf)",
        "thrust_newtons": "Thrust (N)",
        "running_impulse": "Cumulative Impulse (N·s)",
        "temp_casing_f": "Casing Temp (°F)",
        "temp_nozzle_f": "Nozzle Temp (°F)",
        "temp_ambient_f": "Ambient Temp (°F)"
    })
    
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Test Summary", index=False)
        time_df.to_excel(writer, sheet_name="Raw Data", index=False)
        
    print(f"Saved Excel summary workbook to: {out_excel}")
    return out_img, out_excel

def main():
    parser = argparse.ArgumentParser(description="Process rocket motor test stand CSV files")
    parser.add_argument("file", nargs="?", help="CSV file to process (defaults to newest in data/)")
    parser.add_argument("--motor", choices=["J425R", "J435WS", "J450DM", "KNSB-38"], default=None, help="Motor spec to compare against")
    args = parser.parse_args()
    
    if args.file:
        target = args.file
    else:
        # If no file is specified, pick the newest CSV in the data folder
        files = glob.glob(os.path.join(BASE_DIR, "data", "*.csv"))
        if not files:
            print("No CSV files found in data/. Run simulator.py first.")
            return
        target = max(files, key=os.path.getctime)
        
    run_analysis(target, motor_choice=args.motor)

if __name__ == "__main__":
    main()
