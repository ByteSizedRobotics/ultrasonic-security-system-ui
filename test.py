from bleak import BleakClient
import struct
import asyncio

# Replace with your ESP32's MAC Address (find in ESP32 Serial output)
ESP32_MAC_ADDRESS = "18:8b:0e:a9:a8:d6"

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
RX_CHARACTERISTIC_UUID = "abcd1234-5678-1234-5678-abcdef123456"  # Send to ESP32
TX_CHARACTERISTIC_UUID = "dcba4321-8765-4321-8765-654321fedcba"  # Receive from ESP32

async def ble_client():
    async with BleakClient(ESP32_MAC_ADDRESS) as client:
        print("Connected to ESP32!")

        # Example data to send (4x int parameters)
        angle = 45
        distance = 123.45  # Float
        motor_speed = 300
        alarm_threshold = 50

        # Pack into a 16-byte structure (4x 4-byte values)
        tx_data = struct.pack("ifii", angle, distance, motor_speed, alarm_threshold)

        print(f"Sending: Angle={angle}, Distance={distance}, Motor Speed={motor_speed}, Alarm Threshold={alarm_threshold}")
        await client.write_gatt_char(RX_CHARACTERISTIC_UUID, tx_data, response=True)

        # Callback function for receiving data
        def notification_handler(sender, data):
            # Unpack received 24-byte structure
            angle, distance, motor_speed, alarm_threshold, max_distance, sleep_timeout = struct.unpack("ifiiii", data)
            print(f"Received: Angle={angle}, Distance={distance:.2f} cm")
            print(f"Motor Speed={motor_speed}, Alarm Threshold={alarm_threshold}, Max Distance={max_distance}, Sleep Timeout={sleep_timeout}")

        # Subscribe to notifications
        await client.start_notify(TX_CHARACTERISTIC_UUID, notification_handler)

        # Keep running to receive notifications
        print("Listening for BLE data...")
        await asyncio.sleep(30)  # Adjust based on how long you want to test
        await client.stop_notify(TX_CHARACTERISTIC_UUID)

asyncio.run(ble_client())
