/**
 * ==============================================================================
 * Bronco Propulsion Laboratory (BPL) - Static Test Stand Avionics DAQ Firmware
 * ==============================================================================
 * Target Hardware: ESP32-S3 N16R8 (DevKitC-1)
 * Author: BPL Software & Electronics Subteams (Tyler Howard, David Insignares)
 * AIAA Pegasus Chapter, Western Michigan University
 *
 * Pinout Strictly Follows KiCad Schematic Rev 2:
 * ------------------------------------------------------------------------------
 * [1] TI ADS1256 24-bit ADC (Load Cell / Thrust Measurement) via FSPI (SPI2):
 *     - CS:       GPIO 10
 *     - MOSI:     GPIO 11
 *     - SCLK:     GPIO 12
 *     - MISO:     GPIO 13
 *     - DRDY:     GPIO 14  (Hardware Interrupt, Active-Low)
 *     - RST/PDWN: GPIO 9
 *
 * [2] 3x MAX31856 Thermocouple Amplifiers via HSPI (SPI3):
 *     - SCK:      GPIO 4   (Shared)
 *     - MISO:     GPIO 5   (Shared)
 *     - MOSI:     GPIO 6   (Shared)
 *     - CS TC1:   GPIO 7   (Casing Temperature)
 *     - CS TC2:   GPIO 15  (Forward Closure)
 *     - CS TC3:   GPIO 16  (Nozzle Temperature)
 *
 * [3] High-Speed MicroSD Card Logger via Native 4-bit SDMMC:
 *     - CLK:      GPIO 38
 *     - CMD:      GPIO 39
 *     - D0:       GPIO 40
 *     - D1:       GPIO 41
 *     - D2:       GPIO 42
 *     - D3:       GPIO 2
 * ==============================================================================
 */

#include <Arduino.h>
#include <SPI.h>
#include <FS.h>
#include <SD_MMC.h>
#include <WiFi.h>
#include <WiFiUdp.h>

// ----------------- Pin Definitions (KiCad Rev 2) -----------------
#define PIN_ADS_CS        10
#define PIN_ADS_MOSI      11
#define PIN_ADS_SCLK      12
#define PIN_ADS_MISO      13
#define PIN_ADS_DRDY      14
#define PIN_ADS_RST       9

#define PIN_MAX_SCK       4
#define PIN_MAX_MISO      5
#define PIN_MAX_MOSI      6
#define PIN_MAX_CS_TC1    7
#define PIN_MAX_CS_TC2    15
#define PIN_MAX_CS_TC3    16

// ----------------- Telemetry & Logging Configuration -------------
const char* AP_SSID = "BPL_TestStand_Avionics";
const char* AP_PASS = "BroncoPropulsion2026";
const int   UDP_PORT = 4242;
IPAddress   udpBroadcast(192, 168, 4, 255);
WiFiUDP     udp;

File logFile;
bool sdCardActive = false;
volatile bool newSampleReady = false;

// Calibration scale factor: Raw 24-bit ADC counts to pounds of force (lbf)
// Will be tuned during dead-weight cinderblock calibration (e.g. 25 lb block)
float calibration_counts_per_lbf = 33500.0; 
float zero_tare_offset = 0.0;

// Data packet structure pushed from Core 1 to Core 0 via FreeRTOS Queue
struct SensorPacket {
    uint32_t timestamp_ms;
    float    thrust_lbf;
    float    temp_casing_f;
    float    temp_nozzle_f;
    float    temp_ambient_f;
};

QueueHandle_t dataQueue;

// ----------------- Interrupt Service Routine (ISR) ---------------
void IRAM_ATTR ads1256_drdy_isr() {
    newSampleReady = true;
}

// ----------------- Core 1 Task: High-Speed Sampling -------------
void TaskSamplingCore1(void *pvParameters) {
    pinMode(PIN_ADS_DRDY, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_ADS_DRDY), ads1256_drdy_isr, FALLING);

    uint32_t lastTempRead = 0;
    float current_tc1 = 72.0;
    float current_tc2 = 72.0;
    float current_tc3 = 72.0;

    for (;;) {
        // Wait for ADC Data Ready interrupt or poll at 200 Hz
        vTaskDelay(pdMS_TO_TICKS(5)); // 200 Hz loop rate
        
        uint32_t now = millis();
        
        // Mock / Read ADS1256 ADC Value
        int32_t raw_adc = 0; // Replace with SPI transfer when connected
        float measured_thrust = (raw_adc - zero_tare_offset) / calibration_counts_per_lbf;
        if (measured_thrust < 0.0) measured_thrust = 0.0;

        // Thermocouples don't need 200 Hz (they heat up slowly, read at 10 Hz)
        if (now - lastTempRead >= 100) {
            lastTempRead = now;
            // Read 3x MAX31856 over HSPI
            // current_tc1 = read_max31856(PIN_MAX_CS_TC1);
            // current_tc2 = read_max31856(PIN_MAX_CS_TC2);
            // current_tc3 = read_max31856(PIN_MAX_CS_TC3);
        }

        SensorPacket pkt;
        pkt.timestamp_ms = now;
        pkt.thrust_lbf = measured_thrust;
        pkt.temp_casing_f = current_tc1;
        pkt.temp_nozzle_f = current_tc3;
        pkt.temp_ambient_f = current_tc2;

        xQueueSend(dataQueue, &pkt, 0);
    }
}

// ----------------- Setup & Core 0 Loop ---------------------------
void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n[+] BPL Static Test Stand Avionics Booting...");

    // 1. Create FreeRTOS Queue for safe inter-core data transfer
    dataQueue = xQueueCreate(256, sizeof(SensorPacket));

    // 2. Initialize MicroSD Card in 4-bit SDMMC Mode
    if (SD_MMC.begin("/sdcard", false)) { // false = 4-bit mode
        sdCardActive = true;
        logFile = SD_MMC.open("/bpl_test_stand_log.csv", FILE_APPEND);
        if (logFile) {
            logFile.println("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f");
            logFile.flush();
            Serial.println("[✓] MicroSD Card Mounted (4-bit High Speed)");
        }
    } else {
        Serial.println("[!] MicroSD Card Mount Failed. Logging to Serial only.");
    }

    // 3. Initialize Wi-Fi Access Point for Wireless Telemetry
    WiFi.softAP(AP_SSID, AP_PASS);
    udp.begin(UDP_PORT);
    Serial.print("[✓] Telemetry Wi-Fi AP Online: ");
    Serial.println(WiFi.softAPIP());

    // 4. Pin High-Speed Sampling Task to Core 1
    xTaskCreatePinnedToCore(
        TaskSamplingCore1,
        "SamplingTask",
        4096,
        NULL,
        2,  // High priority
        NULL,
        1   // Run on Core 1
    );

    Serial.println("[✓] Avionics Ready for Armed Testing.\n");
}

void loop() {
    // Core 0 handles disk I/O, USB Serial, and Wi-Fi packets
    SensorPacket pkt;
    if (xQueueReceive(dataQueue, &pkt, portMAX_DELAY) == pdTRUE) {
        char buffer[128];
        snprintf(buffer, sizeof(buffer), "%lu,%.2f,%.1f,%.1f,%.1f",
                 pkt.timestamp_ms, pkt.thrust_lbf, pkt.temp_casing_f,
                 pkt.temp_nozzle_f, pkt.temp_ambient_f);

        // 1. Print over USB Serial
        Serial.println(buffer);

        // 2. Write to MicroSD Card
        if (sdCardActive && logFile) {
            logFile.println(buffer);
            // Periodic flush to prevent data loss on sudden power-off
            static uint32_t lastFlush = 0;
            if (millis() - lastFlush > 500) {
                logFile.flush();
                lastFlush = millis();
            }
        }

        // 3. Broadcast over Wi-Fi UDP to Ground Station Laptop
        udp.beginPacket(udpBroadcast, UDP_PORT);
        udp.write((const uint8_t*)buffer, strlen(buffer));
        udp.endPacket();
    }
}
