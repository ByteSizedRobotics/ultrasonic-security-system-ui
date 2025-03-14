#include <Arduino.h>

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// UUID for the service and characteristic
#define SERVICE_UUID        "12345678-1234-1234-1234-1234567890ab"
#define CHARACTERISTIC_UUID "abcdefab-1234-1234-1234-1234567890ab"

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
    
    // Create characteristic with NOTIFY, READ, and WRITE properties
    pCharacteristic = pService->createCharacteristic(
                          CHARACTERISTIC_UUID,
                          BLECharacteristic::PROPERTY_READ | 
                          BLECharacteristic::PROPERTY_WRITE |
                          BLECharacteristic::PROPERTY_NOTIFY  // Enable NOTIFY
                      );
    
    // Start the service
    pService->start();

    // Start advertising
    BLEAdvertising *pAdvertising = pServer->getAdvertising();
    pAdvertising->start();
}

void loop() {
  uint8_t data[8];
  if (Serial1.available() >= 8) {
      Serial1.readBytes(data, 8);

      int angle;
      float distance;

      memcpy(&angle, data, sizeof(angle));
      memcpy(&distance, data + sizeof(angle), sizeof(distance));

      Serial.printf("Received: Angle = %d, Distance = %.2f cm\n", angle, distance);

      // Send data over BLE
      pCharacteristic->setValue(data, sizeof(data));
      pCharacteristic->notify();
  }
  delay(10);
}

