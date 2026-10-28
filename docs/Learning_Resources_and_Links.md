# BPL Software & Data Processing — Helpful Learning Links

Here are some helpful links, videos, and docs for anyone on the team looking to get up to speed on how our rocket test stand code, sensors, and data processing work.

---

### 1. Rocket Motors & Thrust Curves (The Basics)
* **ThrustCurve.org (Motor Database):**  
  [https://www.thrustcurve.org/](https://www.thrustcurve.org/)  
  *Search any motor we test (like the Aerotech J425R or J435WS) to see official thrust graphs, burn times, and downloadable data files.*
* **Richard Nakka's Experimental Rocketry:**  
  [https://www.nakka-rocketry.net/](https://www.nakka-rocketry.net/)  
  *The rocketry bible for amateur solid motors and KNSB (sugar propellant). Great practical explanations of total impulse, chamber pressure, and nozzle design.*
* **How Rocket Motor Classes Work (A to O scale):**  
  [https://en.wikipedia.org/wiki/Model_rocket_motor_classification](https://en.wikipedia.org/wiki/Model_rocket_motor_classification)  
  *A quick breakdown of how motor letters work (each letter has double the total push of the previous letter).*

---

### 2. The Scale & Force Sensors (Load Cells)
* **SparkFun Load Cell & Amplifier Getting Started Guide:**  
  [https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide](https://learn.sparkfun.com/tutorials/load-cell-amplifier-hx711-breakout-hookup-guide)  
  *Great visual guide explaining how strain gauges and S-beam load cells convert physical push into electrical millivolts.*
* **TI ADS1256 Overview (24-bit ADC):**  
  [https://www.ti.com/product/ADS1256](https://www.ti.com/product/ADS1256)  
  *Datasheet and app notes for our analog-to-digital chip. Explains why 24-bit gives us way cleaner force readings than an Arduino's built-in 10-bit pin.*
* **Load Cell Calibration Tutorial:**  
  [https://circuitdigest.com/microcontroller-projects/arduino-weight-measurement-using-load-cell-and-hx711](https://circuitdigest.com/microcontroller-projects/arduino-weight-measurement-using-load-cell-and-hx711)  
  *Simple walkthrough of how to calibrate a scale using a known physical weight (like our 25 lb cinderblocks).*

---

### 3. Temperature Sensors (Thermocouples)
* **Adafruit MAX31856 Universal Thermocouple Amplifier Guide:**  
  [https://learn.adafruit.com/adafruit-max31856-thermocouple-amplifier](https://learn.adafruit.com/adafruit-max31856-thermocouple-amplifier)  
  *Explains Type-K thermocouples, how cold-junction compensation works, and how to wire the SPI bus.*

---

### 4. ESP32-S3 & Arduino Multithreading
* **Random Nerd Tutorials — ESP32 Dual Core with FreeRTOS:**  
  [https://randomnerdtutorials.com/esp32-dual-core-arduino-ide/](https://randomnerdtutorials.com/esp32-dual-core-arduino-ide/)  
  *Best beginner-friendly guide showing how to run sensor reading on Core 1 while writing files on Core 0 so the chip never skips a reading.*
* **ESP32 MicroSD (SD_MMC) High-Speed Logging Guide:**  
  [https://randomnerdtutorials.com/esp32-microsd-card-arduino/](https://randomnerdtutorials.com/esp32-microsd-card-arduino/)  
  *Covers wiring, formatting, and high-speed write loops to prevent buffer overruns.*

---

### 5. Live Telemetry & Mission Control Displays
* **Serial Studio (Open-Source Ground Station):**  
  [https://serial-studio.github.io/](https://serial-studio.github.io/)  
  *A popular free dashboard program used by university teams. You give it a JSON file describing your sensor data, and it builds live dials, gauges, and line plots automatically.*
* **William Osman — COSMOS and Arduino $20 Telemetry:**  
  [https://www.youtube.com/watch?v=0w5qP-w8Y8s](https://www.youtube.com/watch?v=0w5qP-w8Y8s)  
  *Fun, accessible video referenced in our initial research about streaming live sensor data to a laptop ground station.*

---

### 6. Python Data Processing & Graphing
* **Pandas Getting Started Tutorials:**  
  [https://pandas.pydata.org/docs/getting_started/intro_tutorials/](https://pandas.pydata.org/docs/getting_started/intro_tutorials/)  
  *Short, practical lessons on reading CSV files, filtering columns, and calculating stats.*
* **Matplotlib Pyplot Tutorial:**  
  [https://matplotlib.org/stable/tutorials/pyplot.html](https://matplotlib.org/stable/tutorials/pyplot.html)  
  *Clear examples on formatting line graphs, adding labels, setting limits, and saving PNG figures.*
* **NumPy Trapezoidal Rule (Area Under the Curve):**  
  [https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html](https://numpy.org/doc/stable/reference/generated/numpy.trapezoid.html)  
  *Documentation on `np.trapezoid`, which is the exact function our `processor.py` uses to calculate total rocket impulse.*
