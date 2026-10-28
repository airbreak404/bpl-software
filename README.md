# Bronco Propulsion Laboratory (BPL) - Software & DAQ

WMU AIAA Pegasus Chapter  
Subteam: Software  
Team Members: Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez

---

## What is this?

This repository contains the software suite developed for the BPL Static Test Stand.

During a rocket motor static fire, the motor is clamped down into the test stand and fired for approximately 1.5 to 2.5 seconds. Our system handles three main tasks:
1. **Sensor Acquisition:** An ESP32-S3 reads the load cell scale and three thermocouple temperature probes 200 times per second.
2. **Local & Remote Logging:** All readings are written directly to a high-speed MicroSD card on the stand while simultaneously broadcasting live telemetry over Wi-Fi back to a laptop.
3. **Post-Test Data Processing:** Python scripts parse the raw test logs, calculate performance metrics (peak force, average force, burn duration, total impulse, motor classification), and generate publication-quality charts and formatted Excel summaries.

---

## Repository Structure

```
BPL_Software/
├── README.md                          # Subteam documentation and instructions
├── requirements.txt                   # Python package dependencies
├── processor.py                       # Post-test analysis (charts + Excel summaries)
├── simulator.py                       # Test data generator (J425R, J435WS, J450DM, KNSB)
├── ground_station.py                  # Live telemetry receiver & terminal dashboard
├── bpl_serial_studio_dashboard.json   # Serial Studio real-time visualizer config
├── docs/                              # PDR presentation, notes, and research
│   ├── BPL_Software_PDR.pptx          # Official Software PDR slide deck
│   ├── PDR_Talking_Points.md          # 1-page quick reference sheet for PDR
│   ├── Data_Processing_Research.docx  # Subteam research & ESP32 migration notes
│   └── Learning_Resources_and_Links.md# Curated rocketry, DAQ & Python guides
├── firmware/
│   └── bpl_test_stand_esp32.ino       # Dual-core ESP32-S3 firmware (KiCad Rev 2)
├── data/                              # Test run CSV logs
└── reports/                           # Generated report charts (.png) and workbooks (.xlsx)
```

---

## Getting Started

### 1. Python Environment Setup
Install the required packages in a virtual environment:

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Simulated Test Data
To test the software pipeline at home without needing a live rocket motor:
```bash
python simulator.py --motor J425R
```
This generates a realistic test dataset in `data/` simulating ignition transients, combustion noise, burn duration, and heat soaking.

### 3. Run Post-Test Analysis
```bash
python processor.py
```
Automatically locates the latest CSV in `data/`, tares baseline sensor offset, extracts the active burn window (5% peak threshold), calculates total impulse (`np.trapezoid`), and outputs:
* High-resolution plot in `reports/*_report.png`
* Formatted summary spreadsheet in `reports/*_summary.xlsx`

### 4. Run Live Ground Station
```bash
# Live demo simulation:
python ground_station.py --mock

# Live test day listening mode (UDP 4242):
python ground_station.py --port 4242
```
Or open [Serial Studio](https://serial-studio.github.io/) and load `bpl_serial_studio_dashboard.json` for live dials and graphs.
