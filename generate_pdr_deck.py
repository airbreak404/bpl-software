import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

def create_pdr():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    
    # Clean collegiate palette
    COLOR_BG = RGBColor(248, 249, 250)
    COLOR_HEADER_BG = RGBColor(35, 39, 43)
    COLOR_GOLD = RGBColor(204, 153, 0)
    COLOR_DARK = RGBColor(33, 37, 41)
    COLOR_TEXT = RGBColor(60, 64, 67)
    COLOR_WHITE = RGBColor(255, 255, 255)
    
    def add_header(slide, title_text, category="PRELIMINARY DESIGN REVIEW (PDR)"):
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.1))
        tf = header_box.text_frame
        tf.word_wrap = True
        
        p_cat = tf.paragraphs[0]
        p_cat.text = category
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_GOLD
        
        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(24)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_DARK
        
    def add_card(slide, left, top, width, height, title, bullet_points):
        box = slide.shapes.add_shape(1, left, top, width, height)
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(245, 247, 250)
        box.line.color.rgb = RGBColor(218, 222, 229)
        box.line.width = Pt(1)
        
        tb = slide.shapes.add_textbox(left + Inches(0.2), top + Inches(0.15), width - Inches(0.4), height - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p_t = tf.paragraphs[0]
        p_t.text = title
        p_t.font.size = Pt(15)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_DARK
        
        for pt in bullet_points:
            p = tf.add_paragraph()
            p.text = "• " + pt
            p.font.size = Pt(12)
            p.font.color.rgb = COLOR_TEXT
            p.space_after = Pt(4)

    # ------------------------------------------
    # SLIDE 1: Title
    # ------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(1, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = COLOR_HEADER_BG
    bg1.line.fill.background()
    
    tbox = s1.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11.0), Inches(3.0))
    tf1 = tbox.text_frame
    tf1.word_wrap = True
    
    p0 = tf1.paragraphs[0]
    p0.text = "BRONCO PROPULSION LABORATORY | AIAA WMU"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_GOLD
    p0.space_after = Pt(10)
    
    p1 = tf1.add_paragraph()
    p1.text = "Software & Data Acquisition (DAQ)"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_WHITE
    p1.space_after = Pt(8)
    
    p2 = tf1.add_paragraph()
    p2.text = "Preliminary Design Review (PDR) — Static Test Stand"
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(200, 205, 210)
    p2.space_after = Pt(24)
    
    p3 = tf1.add_paragraph()
    p3.text = "Software Subteam: Tyler Howard, Sarah Marcinkiewicz, Sofia Martinez\nTeam Lead: Olivia Perez | Faculty Advisor: Dr. O'Connell"
    p3.font.size = Pt(13)
    p3.font.color.rgb = COLOR_GOLD

    # ------------------------------------------
    # SLIDE 2: 1.0 Overview & Goals
    # ------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "1.0 Overview: Purpose & Subsystem Requirements")
    
    add_card(s2, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
             "Subsystem Purpose", [
                 "Record force and temperature during 1.5 to 2.5 second motor burns.",
                 "Provide a live screen at the laptop bunker so the team can monitor tests safely.",
                 "Save every data point locally on the rig so we never lose data if wireless drops.",
                 "Process raw test numbers into clean engineering graphs for our reports.",
                 "Compare our real test curves directly against manufacturer motor specs."
             ])
             
    add_card(s2, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Key Requirements", [
                 "Sampling Speed: 200 readings per second (200 Hz / 5ms intervals).",
                 "Force Precision: 24-bit ADC for clear thrust resolution on the 250 lb load cell.",
                 "Dual Storage: High-speed MicroSD card on the stand + live Wi-Fi stream to laptop.",
                 "Auto-Tare: Software automatically zeroes out the scale weight right before ignition.",
                 "Turnaround: Instant graph generation (< 1 second) once data is downloaded.",
                 "Cost: $0.00 spent on software licenses (all built on Python and Arduino)."
             ])

    # ------------------------------------------
    # SLIDE 3: 2.0 References
    # ------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "2.0 References: Senior Design Data & Rocketry Standards")
    
    add_card(s3, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "Previous Senior Design Files", [
                 "Reviewed the 2024-2025 WMU Senior Design test logs (J1799, J425, L2200 runs).",
                 "Found that the old Arduino Uno dropped data samples whenever it tried to write to storage.",
                 "Upgraded to an ESP32-S3 chip with two CPU cores to separate sensor reading from file writing.",
                 "Adopted the same physical load cell calibration techniques (using 25 lb weights)."
             ])
             
    add_card(s3, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "Standards & Guidelines", [
                 "NASA-STD-5005D ground support instrumentation guidelines.",
                 "NFPA 1125 / 1127 safety codes for rocket motor ground testing.",
                 "NAR / TRA rocket motor letter class definitions (A through M).",
                 "Safety perimeter rule: software operates wirelessly from >100 feet away."
             ])
             
    add_card(s3, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "Commercial Test Motors", [
                 "Aerotech J425R: 102 lbs peak force, 139 N-sec total push, 1.6s burn time.",
                 "Aerotech J435WS: 156.5 lbs peak force, 174 N-sec total push, 1.7s burn time.",
                 "Aerotech J450DM: 125 lbs peak force, 247 N-sec total push, 2.4s burn time.",
                 "These specs are pre-loaded in our software so we can overlay them on real data."
             ])

    # ------------------------------------------
    # SLIDE 4: 3.0 Proposed Solution - Software Stack
    # ------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "3.0 Proposed Solution: Software Architecture")
    
    add_card(s4, Inches(0.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "1. Rig Firmware (ESP32-S3)", [
                 "Dual-Core task split:",
                 "• Core 1: Listens to the ADC interrupt at 200 Hz and grabs raw load cell numbers instantly.",
                 "• Core 0: Writes data chunks to the MicroSD card and sends Wi-Fi packets.",
                 "Keeps sensor timing steady so disk writes never freeze or drop a reading."
             ])
             
    add_card(s4, Inches(4.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "2. Ground Station (Laptop)", [
                 "Runs on the bunker laptop.",
                 "Receives live Wi-Fi UDP packets from the stand.",
                 "Displays live status in real time:",
                 "• Current force (lbs)",
                 "• Peak force seen so far",
                 "• Motor casing & nozzle temperatures",
                 "Saves a backup copy of all data as it arrives."
             ])
             
    add_card(s4, Inches(8.8), Inches(1.8), Inches(3.7), Inches(5.0),
             "3. Data Processor (Python)", [
                 "Automated post-test analysis tool (processor.py).",
                 "Takes raw CSV log files from the test.",
                 "Zeroes resting weight and isolates the exact burn window.",
                 "Calculates peak force, average force, burn time, and total impulse.",
                 "Exports clean charts for our engineering reports."
             ])

    # ------------------------------------------
    # SLIDE 5: 3.1 Hardware Interface & Simulator
    # ------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "3.1 Proposed Solution: Hardware Wiring & Simulator")
    
    add_card(s5, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
             "Wiring Pinout (Matches KiCad Rev 2)", [
                 "Microcontroller: ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)",
                 "Load Cell ADC (TI ADS1256 on SPI bus 2):",
                 "  • CS: GPIO 10 | MOSI: GPIO 11 | SCLK: GPIO 12 | MISO: GPIO 13",
                 "  • Data Ready (DRDY): GPIO 14 (Hardware interrupt on Core 1)",
                 "3x Thermocouple Amplifiers (MAX31856 on SPI bus 3):",
                 "  • Shared lines: Clock (GPIO 4), MISO (GPIO 5), MOSI (GPIO 6)",
                 "  • Select pins: Casing (GPIO 7), Ambient (GPIO 15), Nozzle (GPIO 16)",
                 "MicroSD Card Slot:",
                 "  • 4-bit high-speed SDMMC: GPIOs 38, 39, 40, 41, 42, 2"
             ])
             
    add_card(s5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Testing Harness (simulator.py)", [
                 "Built a fake data generator to test our code before the stand is built.",
                 "Simulates realistic physics:",
                 "  • Ignition spike & combustion noise",
                 "  • Propellant burn profile over time",
                 "  • Thermocouple heating curves",
                 "Lets the software team verify all calculations and charts right now on our laptops."
             ])

    # ------------------------------------------
    # SLIDE 6: 4.0 Analysis & Verification
    # ------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "4.0 Analysis: Software Verification on Aerotech J425R Data")
    
    report_img = "/Users/thoward/Documents/AIAA/BPL_Software/reports/simulated_J425R_20261027_180350_report.png"
    if os.path.exists(report_img):
        s6.shapes.add_picture(report_img, Inches(0.8), Inches(1.8), width=Inches(6.8))
        c_left = Inches(7.9)
        c_width = Inches(4.6)
    else:
        c_left = Inches(0.8)
        c_width = Inches(11.7)
        
    add_card(s6, c_left, Inches(1.8), c_width, Inches(5.0),
             "Calculated Results vs Spec", [
                 "Motor: Aerotech J425R (Redline)",
                 "Sampling: 1,320 points @ 200 Hz",
                 "Burn Time: 1.515 sec (Spec: 1.6 sec)",
                 "Peak Force: 102.04 lbs (Spec: 102.0 lbs) [Exact match]",
                 "Average Force: 67.68 lbs (301.1 Newtons)",
                 "Total Impulse: 457.5 N-sec (Class I rating)",
                 "Heating Results:",
                 "  • Casing Temp: Reached 249.8 °F (+177.9 °F rise)",
                 "  • Nozzle Temp: Reached 409.1 °F (+337.2 °F rise)",
                 "Result: The code cleanly filters noise, finds ignition/burnout, and calculates accurate metrics."
             ])

    # ------------------------------------------
    # SLIDE 7: 5.0 Risks & Mitigations
    # ------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "5.0 Risks, Mitigations & Next Steps")
    
    add_card(s7, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
             "Technical Risks & How We Solve Them", [
                 "Risk 1: Wi-Fi drops out during a static fire.",
                 "  -> Solution: The MicroSD card on the stand records independently. Wi-Fi is only for live viewing; all test data is stored locally on flash memory.",
                 "Risk 2: Electrical noise from igniters or wires.",
                 "  -> Solution: 24-bit delta-sigma hardware filtering + moving average smoothing in our software.",
                 "Risk 3: Scale zero-point drifting before fire.",
                 "  -> Solution: Software automatically takes a 500ms tare average right before ignition."
             ])
             
    add_card(s7, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Action Items Ahead of TRR", [
                 "1. Range Test at Field: Verify laptop Wi-Fi reception at 150 ft distance with the stand.",
                 "2. Scale Calibration: Run test code with standard 25 lb cinderblocks on the sensor to lock in exact calibration factor.",
                 "3. Mission Control Polish: Finalize live terminal display layout with Systems subteam."
             ])

    # ------------------------------------------
    # SLIDE 8: 6.0 Budget & Timeline
    # ------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "6.0 Budget & Upcoming Milestones")
    
    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0),
             "Software Subteam Budget", [
                 "Total Software Expenses: $0.00",
                 "  • Python 3: Open-source (Free)",
                 "  • Libraries (pandas, numpy, matplotlib): Free",
                 "  • VS Code & Git: Free",
                 "  • Arduino IDE: Free",
                 "No recurring fees or proprietary software costs.",
                 "Leaves 100% of club funds ($4,401) for metal, motors, and hardware."
             ])
             
    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0),
             "Key Dates", [
                 "Oct 28: Preliminary Design Review (PDR).",
                 "Nov 1-15: Connect ESP32 to Electronics PCB.",
                 "Nov 20: Bench test load cell calibration with weights.",
                 "Dec 2: Test Readiness Review (TRR).",
                 "Dec 5: Static Fire at Michiana site with commercial motors.",
                 "Dec 10: Final test report and thrust curves."
             ])

    out_file = "/Users/thoward/Documents/AIAA/BPL_Software/BPL_Software_PDR.pptx"
    prs.save(out_file)
    print(f"Generated clean PDR deck: {out_file}")

if __name__ == "__main__":
    create_pdr()
