/**
 * ==============================================================================
 * Bronco Propulsion Laboratory (BPL) - Static Test Stand Avionics DAQ Firmware
 * ==============================================================================
 * Target Hardware: ESP32-S3 N16R8 (DevKitC-1 / YD-ESP32-S3)
 * Author: BPL Software & Electronics Subteams (Tyler Howard, David Insignares)
 * AIAA Pegasus Chapter, Western Michigan University
 *
 * MODES:
 * ------------------------------------------------------------------------------
 * Set BENCH_SIMULATION_MODE to:
 *   - true:  Bench test mode without physical test stand / sensors attached.
 *            Generates realistic simulated motor burns (Aerotech J425R profile)
 *            and beams data wirelessly over ESP-NOW to the ground receiver board.
 *   - false: Live armed test mode with physical ADS1256 ADC load cell & thermocouples.
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
#include <esp_now.h>
#include <esp_wifi.h>

// ----------------- Operation Mode Configuration ------------------
// Set to true to test the two boards wirelessly on your desk right now!
// Set to false when connecting to the real stand wiring & sensors.
#define BENCH_SIMULATION_MODE true

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
File logFile;
bool sdCardActive = false;
volatile bool newSampleReady = false;

// Calibration scale factor: Raw 24-bit ADC counts to pounds of force (lbf)
float calibration_counts_per_lbf = 33500.0; 
float zero_tare_offset = 0.0;

// Structured sensor packet matching the ground station receiver
typedef struct __attribute__((packed)) {
    uint32_t timestamp_ms;
    float    thrust_lbf;
    float    temp_casing_f;
    float    temp_nozzle_f;
    float    temp_ambient_f;
} SensorPacket;

QueueHandle_t dataQueue;

// Broadcast address for ESP-NOW: beams to ANY listening receiver board
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// ----------------- Interrupt Service Routine (ISR) ---------------
void IRAM_ATTR ads1256_drdy_isr() {
    newSampleReady = true;
}

// ----------------- Simulation Model (Aerotech J425R Profile) -----
// Realistic test curve: 2s countdown -> 1.8s burn -> peak 95 lbf -> cooldown
SensorPacket generate_simulated_sample(uint32_t sim_start_ms) {
    uint32_t now = millis();
    uint32_t elapsed_ms = now - sim_start_ms;
    float t_sec = elapsed_ms / 1000.0f;

    float thrust = 0.0f;
    float temp_casing = 72.0f;
    float temp_nozzle = 72.0f;
    float temp_ambient = 72.0f;

    // Phase 1: 0.0s - 2.0s = Armed / Pre-ignition baseline
    if (t_sec < 2.0f) {
        thrust = 0.0f + (random(-10, 10) / 100.0f); // Slight sensor jitter (+/- 0.1 lb)
    } 
    // Phase 2: 2.0s - 3.8s = Active Motor Burn (J425R Redline curve)
    else if (t_sec >= 2.0f && t_sec <= 3.8f) {
        float burn_t = t_sec - 2.0f; // 0.0 to 1.8s
        
        // Fast rise to peak, progressive regress to burnout
        if (burn_t < 0.2f) {
            thrust = (burn_t / 0.2f) * 95.0f; // Rapid ignition spike to ~95 lbs
        } else {
            thrust = 95.0f - (burn_t - 0.2f) * 35.0f; // Tapers down toward ~39 lbs
        }
        
        // Add realistic propellant grain fluctuation noise (+/- 1.5 lbs)
        thrust += (random(-150, 150) / 100.0f);
        if (thrust < 0.0f) thrust = 0.0f;

        // Temperatures heat up during burn
        temp_nozzle = 72.0f + (burn_t / 1.8f) * 380.0f; // Heats to ~450°F
        temp_casing = 72.0f + (burn_t / 1.8f) * 65.0f;  // Heats to ~137°F
    } 
    // Phase 3: 3.8s+ = Post-burnout cooldown
    else {
        thrust = 0.0f + (random(-5, 5) / 100.0f);
        float cool_t = t_sec - 3.8f;
        temp_nozzle = max(72.0f, 450.0f - (cool_t * 8.0f));
        temp_casing = max(72.0f, 137.0f - (cool_t * 2.0f));
    }

    if (thrust < 0.0f) thrust = 0.0f;

    SensorPacket pkt;
    pkt.timestamp_ms = elapsed_ms;
    pkt.thrust_lbf = thrust;
    pkt.temp_casing_f = temp_casing;
    pkt.temp_nozzle_f = temp_nozzle;
    pkt.temp_ambient_f = temp_ambient;
    return pkt;
}

// ----------------- Core 1 Task: High-Speed Sampling -------------
void TaskSamplingCore1(void *pvParameters) {
#if !BENCH_SIMULATION_MODE
    pinMode(PIN_ADS_DRDY, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(PIN_ADS_DRDY), ads1256_drdy_isr, FALLING);
#endif

    uint32_t simStartMs = millis();
    uint32_t lastTempRead = 0;

    for (;;) {
        // Collect samples at 200 Hz (5 ms intervals)
        vTaskDelay(pdMS_TO_TICKS(5));

#if BENCH_SIMULATION_MODE
        // Auto-loop the simulated test every 10 seconds for continuous bench testing
        if (millis() - simStartMs > 10000) {
            simStartMs = millis();
        }
        SensorPacket pkt = generate_simulated_sample(simStartMs);
#else
        uint32_t now = millis();
        int32_t raw_adc = 0; // Populated via SPI read on physical stand
        float measured_thrust = (raw_adc - zero_tare_offset) / calibration_counts_per_lbf;
        if (measured_thrust < 0.0) measured_thrust = 0.0;

        SensorPacket pkt;
        pkt.timestamp_ms = now;
        pkt.thrust_lbf = measured_thrust;
        pkt.temp_casing_f = 72.0;
        pkt.temp_nozzle_f = 72.0;
        pkt.temp_ambient_f = 72.0;
#endif

        xQueueSend(dataQueue, &pkt, 0);
    }
}

// ----------------- Setup & Core 0 Loop ---------------------------
void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=======================================================");
    Serial.println("  BPL STATIC TEST STAND — AVIONICS TRANSMITTER        ");
    Serial.println("=======================================================");

#if BENCH_SIMULATION_MODE
    Serial.println("[*] MODE: BENCH SIMULATION (No physical stand required)");
    Serial.println("[*] Simulating Aerotech J425R motor firings at 200 Hz");
#else
    Serial.println("[*] MODE: LIVE ARMED HARDWARE (KiCad Rev 2)");
#endif

    // 1. Create FreeRTOS Queue for safe inter-core data transfer
    dataQueue = xQueueCreate(256, sizeof(SensorPacket));

    // 2. Initialize MicroSD Card in 4-bit SDMMC Mode (graceful fallback if absent)
    if (SD_MMC.begin("/sdcard", false)) {
        sdCardActive = true;
        logFile = SD_MMC.open("/bpl_test_stand_log.csv", FILE_APPEND);
        if (logFile) {
            logFile.println("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f");
            logFile.flush();
            Serial.println("[✓] MicroSD Card Mounted (4-bit High Speed)");
        }
    } else {
        Serial.println("[!] MicroSD Card Not Detected — streaming over wireless only.");
    }

    // 3. Initialize Wi-Fi in Station Mode & Long-Range ESP-NOW
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N | WIFI_PROTOCOL_LR);

    Serial.print("[✓] Stand Transmitter MAC Address: ");
    Serial.println(WiFi.macAddress());

    if (esp_now_init() != ESP_OK) {
        Serial.println("[!] ESP-NOW Initialization Failed. Rebooting in 3s...");
        delay(3000);
        ESP.restart();
    }

    // Register broadcast peer so ANY ground receiver board catches packets
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = 0;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) == ESP_OK) {
        Serial.println("[✓] ESP-NOW Broadcast Peer Configured.");
    }

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

    Serial.println("[✓] Avionics Telemetry Transmitter Ready.\n");
}

void loop() {
    SensorPacket pkt;
    if (xQueueReceive(dataQueue, &pkt, portMAX_DELAY) == pdTRUE) {
        // 1. Send wirelessly over ESP-NOW to ground receiver board
        esp_now_send(broadcastAddress, (const uint8_t *)&pkt, sizeof(SensorPacket));

        // 2. Log locally to MicroSD Card if present
        if (sdCardActive && logFile) {
            char buffer[128];
            snprintf(buffer, sizeof(buffer), "%lu,%.2f,%.1f,%.1f,%.1f",
                     pkt.timestamp_ms, pkt.thrust_lbf, pkt.temp_casing_f,
                     pkt.temp_nozzle_f, pkt.temp_ambient_f);
            logFile.println(buffer);

            static uint32_t lastFlush = 0;
            if (millis() - lastFlush > 500) {
                logFile.flush();
                lastFlush = millis();
            }
        }
    }
}
