/**
 * ==============================================================================
 * Bronco Propulsion Laboratory (BPL) - Ground Station Receiver ESP32 Firmware
 * ==============================================================================
 * Target Hardware: ESP32-S3 N16R8 (DevKitC-1 / YD-ESP32-S3)
 * Author: BPL Software Subteam (Tyler Howard)
 * AIAA Pegasus Chapter, Western Michigan University
 *
 * Description:
 * Plugs directly into the Ground Station laptop via USB-C.
 * Listens for low-latency, long-range ESP-NOW telemetry packets beamed from
 * the static test stand transmitter board.
 * 
 * When a packet arrives, it formats it as CSV and prints it to the USB
 * Serial port at 115200 baud for ground_station.py and Serial Studio.
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

// Onboard WS2812 RGB LED on YD-ESP32-S3 is on GPIO 48
#define PIN_STATUS_LED 48

// Structured sensor packet matching the test stand transmitter
typedef struct __attribute__((packed)) {
    uint32_t timestamp_ms;
    float    thrust_lbf;
    float    temp_casing_f;
    float    temp_nozzle_f;
    float    temp_ambient_f;
} SensorPacket;

volatile uint32_t packetsReceived = 0;
volatile bool newPacketFlag = false;
SensorPacket latestPacket;

// ESP-NOW Receive Callback (ESP-IDF 5.x / Arduino ESP32 core 3.x compatible)
#if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
void onDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
#else
void onDataRecv(const uint8_t *mac_addr, const uint8_t *data, int len) {
#endif
    if (len == sizeof(SensorPacket)) {
        memcpy(&latestPacket, data, sizeof(SensorPacket));
        packetsReceived++;
        newPacketFlag = true;
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);

    // Initialize RGB LED
    pinMode(PIN_STATUS_LED, OUTPUT);
    neopixelWrite(PIN_STATUS_LED, 10, 10, 0); // Yellow while starting

    Serial.println("\n=======================================================");
    Serial.println("  BPL STATIC TEST STAND — GROUND RECEIVER (ESP-NOW)    ");
    Serial.println("=======================================================");

    // Set Wi-Fi to Station mode for ESP-NOW
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Optional: Set Long Range (LR) mode for maximum open-field distance
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N | WIFI_PROTOCOL_LR);

    Serial.print("[✓] Receiver MAC Address: ");
    Serial.println(WiFi.macAddress());

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("[!] ESP-NOW Initialization Failed. Rebooting in 3s...");
        neopixelWrite(PIN_STATUS_LED, 20, 0, 0); // Red
        delay(3000);
        ESP.restart();
    }

    esp_now_register_recv_cb(onDataRecv);

    Serial.println("[✓] ESP-NOW Receiver Online.");
    Serial.println("[✓] Listening for Stand Telemetry Packets...\n");
    Serial.println("timestamp_ms,thrust_lbf,temp_casing_f,temp_nozzle_f,temp_ambient_f");
    
    // Soft lavender-pink while ready and listening
    neopixelWrite(PIN_STATUS_LED, 12, 2, 10);
}

void loop() {
    if (newPacketFlag) {
        newPacketFlag = false;

        // Print raw CSV row over USB Serial to laptop
        char buffer[128];
        snprintf(buffer, sizeof(buffer), "%lu,%.2f,%.1f,%.1f,%.1f",
                 latestPacket.timestamp_ms,
                 latestPacket.thrust_lbf,
                 latestPacket.temp_casing_f,
                 latestPacket.temp_nozzle_f,
                 latestPacket.temp_ambient_f);

        Serial.println(buffer);
        
        // Flash bright neon pink on packet receive
        neopixelWrite(PIN_STATUS_LED, 35, 2, 22);
    }

    // Small yield for background RTOS tasks
    vTaskDelay(pdMS_TO_TICKS(1));
}
