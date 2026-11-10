# BPL Static Test Stand — Firmware

This directory contains the Arduino C++ firmware for the two ESP32-S3 boards used on the Bronco Propulsion Laboratory (BPL) Static Test Stand.

---

## Architecture: Dual ESP32-S3 Link (ESP-NOW)

```
[ TEST STAND ]                                      [ GROUND STATION ]
+----------------------------+                      +----------------------------+
| Board 2: Transmitter (TX)  |                      | Board 1: Receiver (RX)     |
| ESP32-S3 @ Test Stand      |                      | ESP32-S3 @ Mission Laptop  |
|                            |                      |                            |
| * Core 1: 200 Hz Sampling  |  >>> ESP-NOW >>>     | * Catches wireless packets |
| * Core 0: ESP-NOW & SDMMC  |  (Long-Range 2.4GHz) | * Streams CSV over USB     |
+----------------------------+                      +--------------+-------------+
                                                                   | USB Serial
                                                                   v
                                                    [ Laptop: ground_station.py ]
```

### Why Two Boards?
Standard Wi-Fi direct to a laptop can struggle over 100–300+ feet across an open field. By using a pair of ESP32s communicating directly via **ESP-NOW**, we get an ultra-fast, robust, long-range wireless bridge without needing a router or Wi-Fi hotspot.

---

## 1. Ground Receiver (`firmware/bpl_receiver_esp32`)
* **Board:** Board 1 (Ground Receiver)
* **Function:** Stays plugged into your laptop via USB-C. Catches telemetry packets beamed through the air and forwards them as plain CSV text over USB Serial (115200 baud).
* **LED Status (GPIO 48):**
  * Soft lavender-pink: Ready and listening.
  * Bright neon pink flashes: Actively receiving data packets.

## 2. Test Stand Transmitter (`firmware/bpl_test_stand_esp32`)
* **Board:** Board 2 (Test Stand Transmitter)
* **Function:** Mounts on the physical static test stand. Reads the 24-bit ADC load cell and three thermocouples 200 times per second, logs to high-speed MicroSD, and broadcasts packets over ESP-NOW.
* **Modes (`BENCH_SIMULATION_MODE`):**
  * `true` *(default for desk testing)*: Simulates an Aerotech J425R motor firing so the team can rehearse and test the ground station without the physical stand.
  * `false` *(live test day)*: Reads the real hardware sensors.

### KiCad Rev 2 Hardware Pinout
| Component | Function | ESP32-S3 Pin | Bus |
| :--- | :--- | :--- | :--- |
| **TI ADS1256 (24-bit ADC)** | Load Cell Thrust | GPIO 10 (CS), 11 (MOSI), 12 (SCLK), 13 (MISO), 14 (DRDY) | SPI2 (FSPI) |
| **3x MAX31856** | Casing Thermocouple (TC1) | GPIO 7 (CS) | SPI3 (HSPI) |
| **3x MAX31856** | Forward Closure (TC2) | GPIO 15 (CS) | SPI3 (HSPI) |
| **3x MAX31856** | Nozzle Thermocouple (TC3) | GPIO 16 (CS) | SPI3 (HSPI) |
| **MicroSD Logger** | High-Speed 4-bit Log | GPIO 38 (CLK), 39 (CMD), 40 (D0), 41 (D1), 42 (D2), 2 (D3) | SDMMC |

---

## How to Flash the Boards

### Option A: Arduino IDE
1. Install the **ESP32** board package (`esp32 by Espressif Systems`).
2. Select Board: **ESP32S3 Dev Module**.
3. Settings:
   * **USB CDC On Boot:** Disabled (Default)
   * **Flash Size:** 16MB (128Mb)
   * **PSRAM:** OPI PSRAM
4. Open the sketch and click **Upload**.

### Option B: Arduino CLI
```bash
# Flash Receiver:
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi firmware/bpl_receiver_esp32
arduino-cli upload -p /dev/cu.usbmodem* --fqbn esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi firmware/bpl_receiver_esp32

# Flash Transmitter:
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi firmware/bpl_test_stand_esp32
arduino-cli upload -p /dev/cu.usbmodem* --fqbn esp32:esp32:esp32s3:CDCOnBoot=default,FlashSize=16M,PSRAM=opi firmware/bpl_test_stand_esp32
```
