# Bronco Propulsion Laboratory (BPL) — Avionics & Software DAQ

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Hardware](https://img.shields.io/badge/hardware-ESP32--S3-green.svg)](https://www.espressif.com/en/products/socs/esp32-s3)
[![Protocol](https://img.shields.io/badge/wireless-ESP--NOW-purple.svg)](https://www.espressif.com/en/solutions/low-power-solutions/esp-now)
[![License](https://img.shields.io/badge/team-WMU%20AIAA-orange.svg)](https://github.com/airbreak404/bpl-software)

Official software, firmware, and ground station data acquisition system for the **Bronco Propulsion Laboratory (BPL) Static Test Stand** at Western Michigan University.

---

## What Does This Project Do?

When we test a solid rocket motor on the test stand, the motor fires for about 1.5 to 2.5 seconds. Our avionics and software system handles three critical jobs:

1. **High-Speed Sensor Reading (200 Hz):** Reads the thrust scale (load cell) and three temperature sensors 200 times every second.
2. **Dual-Board Wireless Telemetry:** An onboard ESP32-S3 logs all raw data to a MicroSD card and beams real-time data through the air via **ESP-NOW** to a receiver board plugged into the mission laptop.
3. **Automated Data Processing:** Python software zeroes the scale, isolates the rocket burn window, calculates peak thrust, average thrust, burn time, and total impulse, and exports clean graphs and Excel reports in seconds.

---

## System Architecture

```
┌───────────────────────────────────────┐                 ┌───────────────────────────────────────┐
│     STAND AVIONICS (Transmitter)      │                 │     GROUND STATION (Receiver)         │
│     ESP32-S3 @ Static Test Stand      │                 │     ESP32-S3 @ Mission Laptop         │
├───────────────────────────────────────┤                 ├───────────────────────────────────────┤
│ • 24-bit ADC Load Cell (Thrust Force) │   ESP-NOW 2.4G  │ • Catches wireless telemetry packets  │
│ • 3x MAX31856 Probes (Temperatures)   │ ───────────────>│ • Streams CSV lines over USB Serial   │
│ • High-Speed MicroSD Logger (SDMMC)   │   (Long Range)  └───────────────────┬───────────────────┘
│ • Built-in J425R Simulation Mode      │                                     │ USB (115200 baud)
└───────────────────────────────────────┘                                     v
                                                          ┌───────────────────────────────────────┐
                                                          │ ground_station.py & Serial Studio     │
                                                          │ • Live terminal telemetry stream      │
                                                          │ • Real-time dials, gauges, and CSV log│
                                                          └───────────────────────────────────────┘
```

---

## Repository Structure

```
BPL_Software/
├── ground_station.py                  # Live telemetry monitor (USB serial & Wi-Fi bridge)
├── processor.py                       # Automated data analysis, thrust curves & Excel reports
├── simulator.py                       # Simulated rocket burn generator (J425R, J435WS, KNSB)
├── calibrate.py                       # Interactive load cell scale calibration tool
├── run_live_monitor.command           # Double-clickable macOS launcher for the ground station
├── requirements.txt                   # Python package dependencies
├── bpl_serial_studio_dashboard.json   # Serial Studio real-time visualizer layout
├── firmware/
│   ├── README.md                      # Flashing guide & KiCad Rev 2 pinout documentation
│   ├── bpl_receiver_esp32/            # Board 1: Ground receiver firmware
│   └── bpl_test_stand_esp32/          # Board 2: Stand transmitter & simulation firmware
├── data/                              # Sample and recorded test CSV logs
├── reports/                           # Output PNG analysis graphs and Excel workbooks
└── docs/                              # PDR slides, test day checklists, and architecture docs
```

---

## Quickstart Guide

### 1. Set Up Python Environment

**Windows:**
```cmd
git clone https://github.com/airbreak404/bpl-software.git
cd bpl-software
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
*(Or simply double-click **`run_live_monitor.bat`**)*

**macOS / Linux:**
```bash
git clone https://github.com/airbreak404/bpl-software.git
cd bpl-software
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
*(Or simply double-click **`run_live_monitor.command`**)*

---

### 2. Live Desk Testing with the Two ESP32 Boards
No physical rocket test stand built yet? No problem! The firmware includes a built-in bench simulation mode:

1. **Plug Board 1 (Receiver)** into your laptop via USB.
   * *Windows automatically assigns it a COM port (`COM3`, `COM4`, etc.). The software auto-detects it!*
2. **Power Board 2 (Transmitter)** with any USB charger, second port, or power bank.
3. Launch the ground station:
   * **Windows:** Double-click `run_live_monitor.bat` (or run `python ground_station.py`)
   * **macOS:** Double-click `run_live_monitor.command` (or run `python ground_station.py`)
4. The receiver will catch the simulated Aerotech J425R motor burn through the air at 200 Hz, display live status in terminal, and log everything to `data/telemetry_<timestamp>.csv`.

### 3. Generate Analysis Graphs & Reports
Run the processor on any captured test CSV:
```bash
python processor.py
```
This automatically:
* Tares the scale baseline weight.
* Identifies ignition, peak thrust, and burnout timestamps.
* Calculates total impulse and motor classification (e.g. `J Class`).
* Generates a high-resolution graph (`reports/*_report.png`) and formatted spreadsheet (`reports/*_summary.xlsx`).

---

## Hardware Pinout (KiCad Schematic Rev 2)

| Subsystem | Sensor / IC | Interface | ESP32-S3 Pins |
| :--- | :--- | :--- | :--- |
| **Thrust Measurement** | TI ADS1256 (24-bit ADC) | SPI2 (FSPI) | `CS: 10`, `MOSI: 11`, `SCLK: 12`, `MISO: 13`, `DRDY: 14` |
| **Casing Temperature** | MAX31856 Thermocouple | SPI3 (HSPI) | `CS: 7`, `SCK: 4`, `MISO: 5`, `MOSI: 6` |
| **Forward Closure Temp** | MAX31856 Thermocouple | SPI3 (HSPI) | `CS: 15`, `SCK: 4`, `MISO: 5`, `MOSI: 6` |
| **Nozzle Temperature** | MAX31856 Thermocouple | SPI3 (HSPI) | `CS: 16`, `SCK: 4`, `MISO: 5`, `MOSI: 6` |
| **Onboard Data Backup** | MicroSD Card Logger | 4-bit SDMMC | `CLK: 38`, `CMD: 39`, `D0: 40`, `D1: 41`, `D2: 42`, `D3: 2` |
| **Status Indicator** | WS2812 RGB LED | Single-Wire | `GPIO 48` |

---

## Team & Credits

**Western Michigan University — AIAA Pegasus Chapter**  
* **Software Subteam:** Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez
* **Electronics / Hardware Subteam:** David Insignares
* **Project Lead:** Alex Fischer

For questions or contributions, submit a pull request or open an issue on [GitHub](https://github.com/airbreak404/bpl-software).
