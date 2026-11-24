/**
 * ==============================================================================
 * BPL Telemetry - Antenna RF Benchmark Transmitter (ESP-NOW)
 * ==============================================================================
 * Target: ESP32-S3 (or any ESP32)
 * Broadcasts rapid test packets to measure RSSI, range, and packet drop.
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

uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
BenchmarkPacket packet;
uint32_t sequenceNumber = 0;

void setup() {
    Serial.begin(115200);
    delay(500);

    pinMode(PIN_STATUS_LED, OUTPUT);
    neopixelWrite(PIN_STATUS_LED, 10, 10, 0); // Yellow initializing

    Serial.println("\n=======================================================");
    Serial.println("  BPL ANTENNA RF BENCHMARK — TRANSMITTER (BEACON)      ");
    Serial.println("=======================================================");

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    // Lock to Channel 1
    esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);

    // Enable maximum 20 dBm TX power
    WiFi.setTxPower(WIFI_POWER_19_5dBm);

    // Support standard Wi-Fi + Long Range (LR)
    esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N | WIFI_PROTOCOL_LR);

    if (esp_now_init() != ESP_OK) {
        Serial.println("[!] ESP-NOW Init Failed");
        neopixelWrite(PIN_STATUS_LED, 25, 0, 0);
        return;
    }

    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = 1;
    peerInfo.encrypt = false;

    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
        Serial.println("[!] Failed to add broadcast peer");
        return;
    }

    Serial.print("[✓] Beacon Active. MAC: ");
    Serial.println(WiFi.macAddress());
    Serial.println("[✓] Broadcasting 20 packets/sec on Channel 1...");
    neopixelWrite(PIN_STATUS_LED, 0, 15, 20); // Cyan ready
}

void loop() {
    sequenceNumber++;
    packet.seq = sequenceNumber;
    packet.uptime_ms = millis();
    packet.tx_power = 20;

    esp_now_send(broadcastAddress, (uint8_t *)&packet, sizeof(BenchmarkPacket));

    // Blink neon pink on transmission
    neopixelWrite(PIN_STATUS_LED, 30, 2, 20);
    delay(10);
    neopixelWrite(PIN_STATUS_LED, 0, 2, 5);

    delay(40); // 50 ms total interval = 20 Hz
}
