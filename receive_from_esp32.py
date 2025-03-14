import asyncio
import struct
from bleak import BleakClient

CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-1234567890ab"

async def run():
    device_address = "18:8b:0e:a9:a8:d6"
    
    async with BleakClient(device_address) as client:
        print(f"Connected: {client.is_connected}")

        # Start receiving notifications
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        # Keep the connection alive
        while True:
            await asyncio.sleep(1)

# Define a function to handle notifications
def notification_handler(sender: int, data: bytearray):
    if len(data) == 8:
        angle, distance = struct.unpack('if', data)  # 'if' for int + float
        print(f"Angle: {angle}, Distance: {distance:.2f} cm")
    else:
        print(f"Warning: Received unexpected data length {len(data)} bytes: {data}")


# Run the asyncio loop
loop = asyncio.get_event_loop()
loop.run_until_complete(run())
