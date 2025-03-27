#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define SERVICE_UUID            "12345678-1234-5678-1234-56789abcdef0"
#define RX_CHARACTERISTIC_UUID  "abcd1234-5678-1234-5678-abcdef123456"  // Receive from Python
#define TX_CHARACTERISTIC_UUID  "dcba4321-8765-4321-8765-654321fedcba"  // Send to Python

BLECharacteristic *txCharacteristic;  // Used to send data

class MyCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) override {
        std::string receivedValue = pCharacteristic->getValue();
        
        if (receivedValue.length() >= 16) { // Expecting at least 16 bytes
            Serial.print("Received from Python: ");

            // Forward the raw bytes to Serial1
            Serial1.write((uint8_t*)receivedValue.data(), receivedValue.length());
        }
    }
};

void setup() {
    Serial.begin(115200);
    Serial1.begin(115200, SERIAL_8N1, 0, 1);  // UART TX=0, RX=1

    // Initialize BLE
    BLEDevice::init("ESP32_BLE");
    BLEServer *pServer = BLEDevice::createServer();
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // RX Characteristic (Receive from Python)
    BLECharacteristic *rxCharacteristic = pService->createCharacteristic(
        RX_CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_WRITE
    );
    rxCharacteristic->setCallbacks(new MyCallbacks());

    // TX Characteristic (Send to Python)
    txCharacteristic = pService->createCharacteristic(
        TX_CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_NOTIFY
    );

    pService->start();
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    BLEDevice::startAdvertising();
    Serial.println("Waiting for BLE connection...");
}

void loop() {
    uint8_t data[24];

    // Read from Serial1 and send via BLE
    if (Serial1.available() >= 24) {
        Serial1.readBytes(data, 24);
        txCharacteristic->setValue(data, sizeof(data));
        txCharacteristic->notify();

        // Debug: Print received fields
        int angle;
        float distance;
        int motor_speed, alarm_threshold, max_distance, sleep_timeout;

        memcpy(&angle, data, sizeof(angle));
        memcpy(&distance, data + sizeof(angle), sizeof(distance));
        memcpy(&motor_speed, data + sizeof(angle) + sizeof(distance), sizeof(motor_speed));
        memcpy(&alarm_threshold, data + sizeof(angle) + sizeof(distance) + sizeof(motor_speed), sizeof(alarm_threshold));
        memcpy(&max_distance, data + sizeof(angle) + sizeof(distance) + sizeof(motor_speed) + sizeof(alarm_threshold), sizeof(max_distance));
        memcpy(&sleep_timeout, data + sizeof(angle) + sizeof(distance) + sizeof(motor_speed) + sizeof(alarm_threshold) + sizeof(max_distance), sizeof(sleep_timeout));

        Serial.printf("Received: Angle = %d, Distance = %.2f cm\n", angle, distance);
        Serial.printf("Motor Speed = %d, Alarm Threshold = %d, Max Distance = %d, Sleep Timeout = %d\n", motor_speed, alarm_threshold, max_distance, sleep_timeout);
    }

    delay(10);
}
