# Bronco Propulsion Laboratory (BPL) - Software & DAQ

WMU AIAA Pegasus Chapter  
Subteam: Software  
Team Members: Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez

---

## What is this?

This folder contains the software we wrote for the BPL Static Test Stand.

During a rocket motor test, the motor is clamped down into the metal stand and fired for about 1.5 to 2.5 seconds. Our system does three main things:
1. **Reads the sensors:** An ESP32 chip reads the scale (load cell) and three temperature probes (thermocouples) hundreds of times per second.
2. **Saves the numbers:** Everything is saved directly to a MicroSD card on the stand so nothing gets lost, while also beaming live readings over Wi-Fi back to a laptop.
3. **Processes the data:** Our Python script takes the raw numbers, calculates how hard the motor pushed (peak force, average force, burn time, total energy), and generates clean charts for our engineering reports.

---

## What each file does

* **`processor.py`**: The main data analysis tool. Feed it a test CSV file, and it zeroes out the scale, finds the exact start/stop time of the motor burn, calculates all the stats, and outputs a clean chart image in the `reports/` folder.
* **`simulator.py`**: A simulator tool. Lets you generate fake test fire CSV files on your laptop (supporting the Aerotech J425R, J435WS, J450DM motors, or our homemade 38mm sugar motor). You can test all your code at home without needing the real stand.
* **`ground_station.py`**: A live terminal monitor. Shows real-time force and temperature readings from a safe distance while logging incoming packets to CSV. Run with `--mock` to see a simulated test in real time.
* **`firmware/bpl_test_stand_esp32.ino`**: The C++ Arduino code that runs on the ESP32-S3 microcontroller on the stand. Maps directly to David's KiCad Rev 2 pinout.
* **`BPL_Software_PDR.pptx`**: Our complete Preliminary Design Review presentation slide deck ready for Olivia and the team.

---

## How to run it

### 1. Activate the Python environment
We have all the required libraries (`pandas`, `numpy`, `matplotlib`, `scipy`) already installed in a local virtual environment:

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

### 3. Process the test and draw graphs
```bash
python processor.py
```
This automatically finds the newest test in `data/`, prints out the numbers (peak force, burn time, total impulse), and saves a chart to `reports/`.

### 4. Run the live ground station (demo mode)
```bash
python ground_station.py --mock
```
Shows a live status dashboard in your terminal while simulating a burn.

---

## Project Structure

```
BPL_Software/
├── README.md               # You are here
├── processor.py            # Post-test analysis and graph generator
├── simulator.py            # Generates test data for testing code
├── ground_station.py       # Live telemetry receiver and dashboard
├── firmware/
│   └── bpl_test_stand_esp32.ino  # ESP32-S3 microcontroller code
├── data/                   # Saved CSV logs
└── reports/                # Saved chart images
```
