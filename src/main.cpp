#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// UUID for the service and characteristic
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcdefab-1234-1234-1234-1234567890ab"

// Callback class to handle received BLE data
class MyCallbacks : public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) override {
        std::string receivedData = pCharacteristic->getValue();
        size_t dataLength = receivedData.length();

        if (dataLength >= 16) { // wait to get 16 bytes of data, 4 bytes per parameter x 4 parameters
            Serial.print("Received via BLE (bytes): ");

            // // Print received bytes in HEX format
            // for (size_t i = 0; i < dataLength; i++) {
            //     Serial.printf("%02X ", (uint8_t)receivedData[i]);
            // }
            // Serial.println();

            // Forward the raw bytes to Serial1 (e.g., STM32)
            Serial1.write((uint8_t*)receivedData.data(), dataLength);
        }
    }
};

void setup() {
    Serial.begin(115200);
    Serial1.begin(115200, SERIAL_8N1, 0, 1);

    // Initialize BLE
    BLEDevice::init("ESP32 BLE Server");
    BLEServer *pServer = BLEDevice::createServer();

    // Print the MAC address of the ESP32
    String macAddress = BLEDevice::getAddress().toString().c_str();
    Serial.println("ESP32 MAC Address: " + macAddress);

    // Create service
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // Create characteristic with READ, WRITE, and NOTIFY properties
    pCharacteristic = pService->createCharacteristic(
        CHARACTERISTIC_UUID,
        BLECharacteristic::PROPERTY_READ | 
        BLECharacteristic::PROPERTY_WRITE |
        BLECharacteristic::PROPERTY_NOTIFY  
    );

    // Attach the callback to handle incoming raw bytes
    pCharacteristic->setCallbacks(new MyCallbacks());

    // Start the service
    pService->start();

    // Start advertising
    BLEAdvertising *pAdvertising = pServer->getAdvertising();
    pAdvertising->start();
}

void loop() {
    uint8_t data[24];
    // sending
    if (Serial1.available() >= 24) {
        Serial1.readBytes(data, 24);

        // Send raw bytes over BLE
        pCharacteristic->setValue(data, sizeof(data));
        pCharacteristic->notify();

        // Used for debugging (displays the different fields of the received data)
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