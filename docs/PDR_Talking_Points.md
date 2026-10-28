# BPL Software Subteam — PDR Quick Talking Points

**Date:** October 28, 2026 (Tonight's PDR Meeting)  
**Who:** Tyler Howard (Software & Data Processing)

---

### The 60-Second Software Pitch (What to say if called on)

> "Hey everyone! For the software and data acquisition side of the static test stand, our main goal is capturing clean force and temperature data during the 1.5 to 2.5 second motor burns, and turning those raw numbers into clean engineering reports.
>
> We have three parts ready:
> 1. **Firmware:** The ESP32-S3 code is mapped to David's KiCad Rev 2 pinout. It uses Core 1 for high-speed sensor interrupts at 200 Hz, and Core 0 to save directly to the MicroSD card and beam live readings over Wi-Fi.
> 2. **Live Ground Station:** A laptop script that lets us watch live thrust and temperatures safely from the bunker over 100 feet away.
> 3. **Data Processor:** A Python tool that ingests the raw test CSV, zeroes the scale, isolates the burn window, calculates peak push, average push, and total impulse, and exports clean PNG charts and Excel summaries.
>
> We also built a test simulator, so we were able to run a simulated Aerotech J425R motor test and verify that our algorithms work accurately before the stand is even built. The presentation deck is complete and uploaded to OneDrive!"

---

### Answers to Likely Questions (Plain English)

* **Q: How fast are we sampling the sensors?**  
  * **Answer:** "200 times per second (200 Hz / 5 millisecond intervals). Because these motors burn out in under 2 seconds, 200 Hz gives us 300 to 500 crisp data points to map the exact thrust curve."
* **Q: What happens if Wi-Fi cuts out in the middle of a test?**  
  * **Answer:** "We don't lose anything. The ESP32 writes every single data point directly to an on-board MicroSD card over high-speed 4-bit SDMMC. Wi-Fi is only for live viewing; the MicroSD card is our permanent, fail-safe record."
* **Q: How do we zero out the weight of the motor and brackets before firing?**  
  * **Answer:** "Our Python processor automatically takes a 500ms average of the scale readings while the motor is sitting idle right before ignition and tares (zeroes) it out."
* **Q: What is our software budget?**  
  * **Answer:** "$0.00. We built everything on open-source Python, VS Code, and Arduino tools, leaving all club funds for metal and rocket motors."
* **Q: What are our next steps after PDR?**  
  * **Answer:** "Bench testing with David once the physical PCB is assembled, and calibrating the load cell with standard 25 lb cinderblocks to verify scale accuracy."
