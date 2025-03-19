import asyncio
import bisect
import random
import struct
import threading
from bleak import BleakClient
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import numpy as np
import plotly.graph_objects as go

CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-1234567890ab"
DEVICE_ADDRESS = "18:8b:0e:a9:a8:d6"

TEST_ANGLE_INCREMENT = 2.5
UPDATE_INTERVAL = 125.0


class SensorData:
    def __init__(self):
        self.previous_angle = 0
        self.current_angle = 0
        self.current_distance = 0
        self.move_forward = True
        self.angles = []
        self.distances = []
        # self.timestamps = []
        # self.timestamp_id = 0

    def test_tick_data(self):
        sensor_data.previous_angle = sensor_data.current_angle
        delta_distance = (
            random.randint(-3, 2)
            if self.current_distance > 50
            else random.randint(-2, 3)
        )
        self.current_distance = max(0, min(self.current_distance + delta_distance, 100))
        if self.move_forward:
            self.current_angle += TEST_ANGLE_INCREMENT
            if self.current_angle >= 180.0:
                self.current_angle = 180.0
                self.move_forward = False
        else:
            self.current_angle -= TEST_ANGLE_INCREMENT
            if self.current_angle <= 0.0:
                self.current_angle = 0.0
                self.move_forward = True

    def update(self):
        left_idx = 0
        right_idx = 0
        if self.previous_angle <= self.current_angle:
            left_idx = bisect.bisect_left(self.angles, self.previous_angle) + 1
            right_idx = bisect.bisect_right(self.angles, self.current_angle)
        else:
            left_idx = bisect.bisect_left(self.angles, self.current_angle)
            right_idx = bisect.bisect_right(self.angles, self.previous_angle) - 1

        print(f"left_idx {left_idx} right_idx {right_idx}")

        self.angles = self.angles[:left_idx] + self.angles[right_idx:]
        self.distances = self.distances[:left_idx] + self.distances[right_idx:]
        # self.timestamps = self.timestamps[:left_idx] + self.timestamps[right_idx:]

        insert_idx = bisect.bisect_left(self.angles, self.current_angle)
        self.angles.insert(insert_idx, self.current_angle)
        self.distances.insert(insert_idx, self.current_distance)
        # self.timestamps.insert(insert_idx, self.timestamp_id)
        # self.timestamp_id += 1


sensor_data = SensorData()

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.H1("Ultrasonic Radar Map"),
        dcc.Graph(id="radar-chart", style={"height": "500px"}),
        dcc.Interval(id="radar-interval", interval=UPDATE_INTERVAL, n_intervals=0),
    ]
)


# Define a function to handle Bluetooth notifications
def notification_handler(sender: int, data: bytearray):
    global sensor_data
    if len(data) == 8:
        sensor_data.current_angle, sensor_data.current_distance = struct.unpack(
            "if", data
        )
    else:
        print(f"Warning: Received unexpected data length {len(data)} bytes: {data}")


# Bluetooth communication logic
async def bluetooth_run():
    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        # Keep the connection alive
        while True:
            await asyncio.sleep(1)


# Start Bluetooth in a separate thread
def start_bluetooth():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bluetooth_run())


# bluetooth_thread = threading.Thread(target=start_bluetooth, daemon=True)
# bluetooth_thread.start()


# Update the radar chart with new data
@app.callback(Output("radar-chart", "figure"), Input("radar-interval", "n_intervals"))
def update_radar_chart(n_intervals):
    global sensor_data

    sensor_data.test_tick_data()

    print(
        f"previous_angle {sensor_data.previous_angle} current_angle {sensor_data.current_angle} current_distance {sensor_data.current_distance}"
    )

    sensor_data.update()
    print(sensor_data.angles)
    print(sensor_data.distances)
    # print(sensor_data.timestamps)
    print()

    fig = go.Figure(
        go.Scatterpolar(
            r=sensor_data.distances,
            theta=sensor_data.angles,
            marker=dict(size=2, color="green"),
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[sensor_data.current_distance],
            theta=[sensor_data.current_angle],
            mode="markers+text",
            marker=dict(size=8, color="green"),
            text=[
                f"Angle: {sensor_data.current_angle}, Distance: {sensor_data.current_distance:.2f} cm"
            ],
            textposition="top center",
        )
    )

    fig.update_layout(
        polar=dict(
            sector=[0, 180],
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        showlegend=False,
    )

    return fig


# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True, use_reloader=False)
