# Bronco Propulsion Laboratory (BPL) - Software & DAQ

WMU AIAA Pegasus Chapter  
Subteam: Software  
Team Members: Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez

---

## What is this?

Software and test tools for the Bronco Propulsion Laboratory (BPL) Static Test Stand at Western Michigan University.

During a static fire test, the motor is clamped down into the test stand and fired for about 1.5 to 2.5 seconds. Our setup handles three main jobs:
1. **Reads the sensors:** An ESP32-S3 reads the load cell scale and three thermocouple temperature probes 200 times per second.
2. **Logs everything:** Saves every reading to an onboard MicroSD card so nothing gets lost, and sends live telemetry over Wi-Fi back to a laptop.
3. **Processes the data:** Python scripts parse the test CSV, calculate peak thrust, average thrust, burn time, total impulse, and motor classification, and export clean graphs and an Excel summary.

---

## Repository Structure

```
BPL_Software/
├── README.md                          # Subteam documentation and instructions
├── requirements.txt                   # Python dependencies (pip install -r requirements.txt)
├── processor.py                       # Post-test analysis (graphs + Excel summaries)
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
└── reports/                           # Output PNG charts and Excel workbooks
```

---

## Setup & Usage

### 1. Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate simulated test data
To test changes at home without needing a live rocket motor:
```bash
python simulator.py --motor J425R
```
This drops a simulated test run into `data/` (with realistic ignition curve, combustion flutter, and thermocouple heating).

### 3. Run post-test analysis
```bash
python processor.py
```
Picks up the newest test in `data/`, zeroes out the scale baseline, finds the burn window, calculates total impulse, and outputs:
* Summary plot: `reports/*_report.png`
* Formatted spreadsheet: `reports/*_summary.xlsx`

### 4. Run live ground station
```bash
# Terminal mock demo:
python ground_station.py --mock

# Live test day listening mode (UDP 4242):
python ground_station.py --port 4242
```
Or open [Serial Studio](https://serial-studio.github.io/) and load `bpl_serial_studio_dashboard.json` for live dials and graphs.
