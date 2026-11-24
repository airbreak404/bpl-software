/**
 * ==============================================================================
 * BPL Telemetry - Antenna RF Benchmark Receiver (ESP-NOW)
 * ==============================================================================
 * Target: ESP32-S3
 * Measures live RSSI (in dBm), packet count, and drop rate.
 * Outputs formatted telemetry over USB Serial for terminal live view.
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#define PIN_STATUS_LED 48

typedef struct __attribute__((packed)) {
    uint32_t seq;
    uint32_t uptime_ms;
    int8_t   tx_power;
} BenchmarkPacket;

volatile uint32_t totalReceived = 0;
volatile uint32_t lastSeq = 0;
volatile uint32_t droppedPackets = 0;
volatile int8_t   currentRSSI = 0;
volatile bool     newPacket = false;
BenchmarkPacket   receivedData;

unsigned long lastHeartbeat = 0;

void onDataRecv(const esp_now_recv_info_t *recv_info, const uint8_t *data, int len) {
    if (len == sizeof(BenchmarkPacket)) {
        memcpy(&receivedData, data, sizeof(BenchmarkPacket));

        if (recv_info && recv_info->rx_ctrl) {
            currentRSSI = recv_info->rx_ctrl->rssi;
        }

        if (totalReceived > 0 && receivedData.seq > lastSeq + 1) {
            droppedPackets += (receivedData.seq - lastSeq - 1);
        }
        lastSeq = receivedData.seq;
        totalReceived++;
        newPacket = true;
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);

    pinMode(PIN_STATUS_LED, OUTPUT);
    neopixelWrite(PIN_STATUS_LED, 10, 10, 0); // Yellow

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Force 2.4 GHz Channel 1
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N | WIFI_PROTOCOL_LR);

    if (esp_now_init() != ESP_OK) {
        Serial.println("[!] ESP-NOW Init Failed");
        neopixelWrite(PIN_STATUS_LED, 25, 0, 0);
        return;
    }

    esp_now_register_recv_cb(onDataRecv);

    Serial.println("\n=======================================================");
    Serial.println("  BPL ANTENNA RF BENCHMARK — RECEIVER ONLINE           ");
    Serial.println("=======================================================");
    Serial.print("[✓] Receiver MAC: ");
    Serial.println(WiFi.macAddress());
    Serial.println("[✓] Radio Channel: 1");
    Serial.println("[✓] Waiting for Beacon Packets from Transmitter...\n");
    Serial.println("CSV:seq,rssi,drops,total_rx");

    neopixelWrite(PIN_STATUS_LED, 10, 2, 10); // Ready lavender
}

void loop() {
    if (newPacket) {
        newPacket = false;

        // Color code onboard LED based on signal strength
        if (currentRSSI >= -65) {
            // Excellent: Emerald green
            neopixelWrite(PIN_STATUS_LED, 0, 30, 10);
        } else if (currentRSSI >= -80) {
            // Decent / Fair: Amber
            neopixelWrite(PIN_STATUS_LED, 25, 15, 0);
        } else {
            // Weak: Crimson red
            neopixelWrite(PIN_STATUS_LED, 35, 0, 0);
        }

        // Output CSV row for easy parsing by Python or Serial Plotter
        Serial.printf("CSV:%lu,%d,%lu,%lu\n", receivedData.seq, currentRSSI, droppedPackets, totalReceived);
    }

    // Heartbeat every 2 seconds if no packets are arriving
    if (millis() - lastHeartbeat >= 2000) {
        lastHeartbeat = millis();
        if (totalReceived == 0) {
            Serial.println("[WAITING] Receiver online on Ch 1. Waiting for Transmitter packets (is TX powered on?)...");
            // Gentle lavender pulse
            neopixelWrite(PIN_STATUS_LED, 15, 0, 15);
        }
    }

    vTaskDelay(pdMS_TO_TICKS(1));
}
