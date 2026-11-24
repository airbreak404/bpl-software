# 🌸 Bronco Propulsion Laboratory (BPL) — Windows Setup & Operation Guide
**Western Michigan University • AIAA Pegasus Chapter • Avionics & Telemetry Subteam**

This guide provides step-by-step instructions for team members running the BPL Mission Control Ground Station on **Windows 10 / Windows 11**.

---

## 1. Prerequisites (One-Time Setup)

### A. Python 3.10+
1. Download the latest Python 3 installer from [python.org/downloads/windows](https://www.python.org/downloads/windows/).
2. Run the installer and **MUST CHECK THE BOX**:
   > ☑ **Add python.exe to PATH** (at the bottom of the installer dialog).
3. Click **Install Now**.

### B. USB Driver (CH343 / CH340 / CP210x)
Our ESP32-S3 ground station boards use WCH CH343 / CH340 or native USB CDC. Windows 11 automatically detects them as `USB Serial Device (COMx)`.
* If your board shows up with a yellow warning triangle in **Device Manager** > **Ports (COM & LPT)**, download the official WCH driver from [wch.cn/downloads/CH341SER_EXE.html](https://www.wch.cn/downloads/CH341SER_EXE.html) or contact the Avionics leads.

---

## 2. Hardware Connection

1. Take the **Ground Receiver ESP32-S3 board** (MAC: `14:c1:9f:3b:e5:4c`).
2. Connect it to your Windows laptop using a USB-C data cable.
3. Open **Device Manager** > expand **Ports (COM & LPT)**:
   * You should see a port such as `USB-SERIAL CH340 (COM3)` or `USB Serial Device (COM5)`.
   * Note: The BPL telemetry server automatically detects this COM port — you do not need to configure anything manually!

---

## 3. Launching Mission Control

1. Open the cloned `bpl-software` folder in Windows File Explorer.
2. Double-click:
   ```text
   Launch_BPL_Web_Dashboard.bat
   ```
3. What happens automatically:
   * The script checks Python and verifies `pyserial`.
   * Automatically launches your default web browser (Edge, Chrome, Brave, or Firefox) to `http://localhost:5050`.
   * The terminal connects to your ESP32 on the detected COM port at **115200 baud**.
   * Telemetry begins streaming live at 200 Hz with Server-Sent Events (SSE).

---

## 4. Browser Compatibility

The BPL Mission Control dashboard is tested and supported across all modern web browsers:
* **Google Chrome:** Native hardware acceleration, recommended.
* **Microsoft Edge:** Fully supported (Chromium engine).
* **Brave Browser:** Fully supported.
* **Mozilla Firefox:** Supported.
* **Safari (macOS / iOS / iPadOS):** Supported over LAN (`http://<laptop-ip>:5050`).

### Audio Telemetry
Click the **`🔇 SFX MUTED`** button in the top-right header to unmute live synthesized telemetry audio tones (thrust frequency ramp and heartbeat pings). Modern browsers require user interaction before playing audio.

---

## 5. Live Telemetry Channels & Indicators

| Indicator | Location | Description |
| :--- | :--- | :--- |
| **Ground Receiver (USB DAQ)** | Top Pill & Card 1 | 🟢 `CONNECTED (COMx @ 115200)` when plugged in; 🔴 `NOT DETECTED` if unplugged. |
| **Stand RF Link (ESP-NOW)** | Annunciator Card 2 | 🟢 `200 Hz LINK ACTIVE` when packets arrive over air; 🟡 `STANDBY (NO RF)` between burns. |
| **Thrust Dynamometer** | Center-Left Dial | Real-time pounds-force (`lbf`) and Newtons (`N`), instantaneous chamber pressure (PSI). |
| **NFPA 1127 Scope** | Center Radar | 360° polar radar with rotating sweep, standoff perimeter rings, and beacon blip. |
| **RF Signal Margin Dial** | Center-Right Dial | Calibrated RSSI (`dBm`), link margin (`+dB`), and drop rate percentage. |
| **200 Hz Rolling Trace** | Bottom-Left Chart | Real-time multi-channel oscilloscope for Thrust, Nozzle Temp, and Casing Temp. |
| **Safety Compliance Matrix** | Bottom-Right Table | Dynamic NFPA 1127 Table 4.16.4 standoff calculations for Motor Classes H through M. |

---

## 6. Troubleshooting

* **Dashboard shows "🔴 GROUND RECEIVER: NOT DETECTED":**
  * Check that your USB-C cable is a **data cable** (some cheap cables are charging-only).
  * Unplug and replug the USB-C cable. The server auto-detects reconnection within 0.5 seconds without restarting the script.
* **Dashboard shows "🟡 STAND RF LINK: STANDBY (NO RF)":**
  * The ground receiver is connected and working, but the stand transmitter board has not sent a packet within the last 1.2 seconds. Ensure the stand board is powered on.
* **Port Permission Denied:**
  * Ensure Serial Studio, Arduino IDE Serial Monitor, or PuTTY are closed so they do not lock the COM port.
