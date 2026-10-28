# Bronco Propulsion Laboratory (BPL) - Software & DAQ

WMU AIAA Pegasus Chapter  
Subteam: Software  
Team Members: Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez

---

## What is this?

This folder contains the software we wrote for the BPL Static Test Stand.

During a rocket motor test, the motor is clamped down into the metal stand and fired for about 1.5 to 2.5 seconds. Our system does three main things:
1. **Reads the sensors:** An ESP32 chip reads the scale (load cell) and three temperature probes (thermocouples) 200 times per second.
2. **Saves the numbers:** Everything is saved directly to a MicroSD card on the stand so nothing gets lost, while also beaming live readings over Wi-Fi back to a laptop.
3. **Processes the data:** Our Python script takes the raw numbers, calculates how hard the motor pushed (peak force, average force, burn time, total energy), and generates clean charts and Excel summaries for our engineering reports.

---

## What each file does

* **`processor.py`**: The main data analysis tool. Feed it a test CSV file, and it zeroes out the scale, finds the exact start/stop time of the motor burn, calculates all the stats, and outputs both a clean chart image (`.png`) and a formatted summary spreadsheet (`.xlsx`) in the `reports/` folder.
* **`simulator.py`**: A simulator tool. Lets you generate fake test fire CSV files on your laptop (supporting the Aerotech J425R, J435WS, J450DM motors, or our homemade 38mm sugar motor). You can test all your code at home without needing the real stand.
* **`ground_station.py`**: A live terminal monitor. Shows real-time force and temperature readings from a safe distance while logging incoming packets to CSV. Run with `--mock` to see a simulated test in real time.
* **`bpl_serial_studio_dashboard.json`**: Ready-to-use project file for Serial Studio (open-source GUI visualizer). Load this into Serial Studio to get live gauges and graphs during a test.
* **`firmware/bpl_test_stand_esp32.ino`**: The C++ Arduino code that runs on the ESP32-S3 microcontroller on the stand. Maps directly to David's KiCad Rev 2 pinout.
* **`BPL_Software_PDR.pptx`**: Our complete Preliminary Design Review presentation slide deck ready for Olivia and the team.
* **`PDR_Talking_Points.md`**: A quick 1-page cheat sheet for tonight's meeting with 60-second talking points and plain-English answers to likely questions.
* **`Learning_Resources_and_Links.md`**: Curated beginner-friendly links explaining load cells, thrust curves, ESP32 multithreading, and Python data analysis.

---

## How to run it

### 1. Activate the Python environment
We have all the required libraries (`pandas`, `numpy`, `matplotlib`, `scipy`, `openpyxl`) already installed in a local virtual environment:

```bash
# Option A: Run directly using the virtual environment python
/Users/thoward/Documents/AIAA/venv/bin/python simulator.py

# Option B: Activate the venv first
source /Users/thoward/Documents/AIAA/venv/bin/activate
python simulator.py
```

### 2. Generate a fake test fire
```bash
python simulator.py --motor J425R
```
This drops a fresh CSV file into `data/`.

### 3. Process the test and draw graphs + excel
```bash
python processor.py
```
This automatically finds the newest test in `data/`, prints out the numbers (peak force, burn time, total impulse), and saves both a chart PNG and an Excel spreadsheet to `reports/`.

### 4. Run the live ground station (demo mode)
```bash
python ground_station.py --mock
```
Shows a live status dashboard in your terminal while simulating a burn.

---

## Project Structure

```
BPL_Software/
├── README.md                          # You are here
├── processor.py                       # Post-test analysis (charts + Excel)
├── simulator.py                       # Generates test data for testing code
├── ground_station.py                  # Live telemetry receiver and dashboard
├── bpl_serial_studio_dashboard.json   # Serial Studio visualizer config
├── PDR_Talking_Points.md              # 1-page cheat sheet for tonight's PDR
├── Learning_Resources_and_Links.md    # Helpful links for the team
├── BPL_Software_PDR.pptx              # Full PDR slide deck
├── firmware/
│   └── bpl_test_stand_esp32.ino       # ESP32-S3 microcontroller code
├── data/                              # Saved CSV logs
└── reports/                           # Saved charts (.png) and summaries (.xlsx)
```
