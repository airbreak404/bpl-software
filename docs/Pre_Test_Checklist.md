# BPL Static Test Stand — Software & DAQ Checklist

A quick step-by-step checklist for the software and telemetry subteam (Tyler, Sarah, Sofia) on test day.

---

### Phase 1: Pre-Departure Bench Prep (On Campus)
- [ ] **Firmware Verification:** Verify ESP32-S3 is flashed with `firmware/bpl_test_stand_esp32.ino` with the calibrated `counts_per_pound` value.
- [ ] **MicroSD Card Check:** Format a high-end Class 10 / U3 MicroSD card to **FAT32**. Verify card mounts cleanly and create an empty root directory.
- [ ] **Laptop Ground Station:** Ensure the laptop has Python installed with `requirements.txt` and battery is charged to 100% (plus a backup charger/power bank).
- [ ] **Serial Studio Dashboard:** Verify `bpl_serial_studio_dashboard.json` loads without errors and connects to UDP port `4242`.

---

### Phase 2: On-Site Stand Setup (At Michiana Bunker)
- [ ] **Power Stand:** Power on the ESP32-S3 test stand transmitter enclosure via the 2S LiPo battery.
- [ ] **Connect Ground Receiver:** Plug Board 1 (Ground Receiver) into the mission laptop USB-C port.
- [ ] **Physical Sensor Sanity Check:**
  - Scale: Should read near `0.0 lbs` resting. Gently press the load cell plate to confirm force needle moves upwards.
  - Thermocouples: All three probes (casing, nozzle, ambient) should read within ±3°F of ambient outdoor temperature (~65°F–75°F).
- [ ] **Establish Telemetry Link:**
  - Launch terminal ground station: `python ground_station.py` (or double click `run_live_monitor.command`)
  - (Optional) Launch Serial Studio and confirm live gauges.
  - Confirm incoming data packets are updating at 200 Hz over ESP-NOW.

---

### Phase 3: T-5 Minute Countdown
- [ ] **Clear the Pad:** All personnel retreat behind the safety perimeter (>100 feet away).
- [ ] **Start File Recording:**
  - Ensure local MicroSD logging is active (green LED steady on stand).
  - Confirm laptop ground station is actively saving incoming telemetry to CSV (`data/telemetry_<timestamp>.csv`).
- [ ] **Zero Tare Verification:** Confirm scale baseline is resting stable within ±0.2 lbs. (Software automatically takes a 500 ms rolling tare prior to ignition).
- [ ] **Ignition Go/No-Go:** Report: *"Software and Data Acquisition is GO for launch."*

---

### Phase 4: Active Burn & Post-Fire Protocol
- [ ] **During Burn (~2 seconds):** Keep eyes on the live thrust spike and confirm peak force registers on the dashboard.
- [ ] **Thermal Soak Monitoring:** Watch the nozzle and casing temperature curve climb to peak (typically 300°F–480°F) and begin cooling down.
- [ ] **Safe Approach Clearance:** **DO NOT APPROACH THE TEST STAND** until nozzle temperature drops below safe handling thresholds (<120°F) and safety officers clear the pad.
- [ ] **Retrieve Master SD Card:** Remove the MicroSD card from the stand and insert it into the laptop.

---

### Phase 5: Post-Test Data Processing (< 2 Minutes)
- [ ] Copy the raw test CSV from the MicroSD card into `data/`.
- [ ] Run the analysis script:
  ```bash
  python processor.py
  ```
- [ ] Review the printed summary:
  - Peak Thrust (lbs & Newtons)
  - Total Impulse (N·s) & Letter Class (e.g. J class)
  - Burn Duration (seconds)
  - Comparison to manufacturer certified spec (% error)
- [ ] Export outputs: PNG plot and Excel summary workbook are ready in `reports/` for immediate review by Olivia, Dr. Burns, and Dr. O'Connell.
