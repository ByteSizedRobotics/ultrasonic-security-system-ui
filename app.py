import argparse
import asyncio
import bisect
import random
import struct
import threading
from bleak import BleakClient
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go


CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-1234567890ab"
DEVICE_ADDRESS = "18:8b:0e:a9:a8:d6"

TEST_ANGLE_INCREMENT = 2.5
UPDATE_INTERVAL = 125.0
WARNING_DISTANCE = 30
DISTANCE_RANGE = 50

# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()
debug_mode = args.debug


class SensorData:
    def __init__(self):
        self.lock = threading.Lock()
        self.previous_angle = 0
        self.current_angle = 0
        self.current_distance = 0
        self.move_forward = True
        self.angles = []
        self.distances = []
        # self.timestamps = []
        # self.timestamp_id = 0

        self.motor_speed = 0
        self.distance_threshold = 0
        self.max_detection_distance = 0
        self.sleep_timeout = 0

    def read_data(self, data):
        self.previous_angle = self.current_angle
        (
            self.current_angle,
            self.current_distance,
            self.motor_speed,
            self.distance_threshold,
            self.max_detection_distance,
            self.sleep_timeout,
        ) = struct.unpack("if", data)

    def test_tick_data(self):
        delta_distance = (
            random.randint(-3, 2)
            if self.current_distance > 30
            else random.randint(-2, 3)
        )
        self.current_distance = max(0, min(self.current_distance + delta_distance, 100))
        if self.move_forward:
            self.current_angle += TEST_ANGLE_INCREMENT
            if self.current_angle >= 90.0:
                self.current_angle = 90.0
                self.move_forward = False
        else:
            self.current_angle -= TEST_ANGLE_INCREMENT
            if self.current_angle <= 0.0:
                self.current_angle = 0.0
                self.move_forward = True

    def update(self):
        left_idx = 0
        right_idx = 0
        if self.previous_angle < self.current_angle:
            left_idx = bisect.bisect_left(self.angles, self.previous_angle) + 1
            right_idx = bisect.bisect_right(self.angles, self.current_angle)
        elif self.previous_angle > self.current_angle:
            left_idx = bisect.bisect_left(self.angles, self.current_angle)
            right_idx = max(
                bisect.bisect_right(self.angles, self.previous_angle) - 1, 0
            )
        else:
            left_idx = bisect.bisect_left(self.angles, self.current_angle)
            right_idx = bisect.bisect_right(self.angles, self.current_angle)

        self.angles = self.angles[:left_idx] + self.angles[right_idx:]
        self.distances = self.distances[:left_idx] + self.distances[right_idx:]
        # self.timestamps = self.timestamps[:left_idx] + self.timestamps[right_idx:]

        print(
            f"Inserting self.current_angle {self.current_angle}, self.current_distance {self.current_distance}"
        )
        insert_idx = bisect.bisect_left(self.angles, self.current_angle)
        self.angles.insert(insert_idx, self.current_angle)
        self.distances.insert(insert_idx, self.current_distance)
        # self.timestamps.insert(insert_idx, self.timestamp_id)
        # self.timestamp_id += 1


sensor_data = SensorData()

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        html.H1("Ultrasonic Radar Map", className="text-center mb-4"),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(
                        id="radar-chart",
                        style={"height": "100%"},
                    ),
                    width=6,
                    className="border border-2 border-secondary p-3 rounded-3",
                ),
                dbc.Col(
                    [
                        html.Div(id="alert-messages"),
                    ],
                    width=6,
                    className="border border-2 border-awrning p-3 rounded-3 h-100",
                ),
            ],
            className="g-4 h-100",
        ),
        dcc.Interval(id="radar-interval", interval=UPDATE_INTERVAL, n_intervals=0),
    ],
    fluid=True,
    className="flex-grow-1 d-flex flex-column p-3",
    style={
        "backgroundColor": "#f8f9fa",
        "margin": "0",
        "padding": "0",
        "height": "90vh",
    },
)


def notification_handler(sender: int, data: bytearray):
    global sensor_data
    if len(data) == 24:
        with sensor_data.lock:
            sensor_data.read_data(data)
    else:
        print(f"Warning: Received unexpected data length {len(data)} bytes: {data}")


async def bluetooth_run():
    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)

        while True:
            await asyncio.sleep(1)


def start_bluetooth():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bluetooth_run())


if not debug_mode:
    bluetooth_thread = threading.Thread(target=start_bluetooth, daemon=True)
    bluetooth_thread.start()


@app.callback(Output("radar-chart", "figure"), Input("radar-interval", "n_intervals"))
def update_radar_chart(n_intervals):
    global sensor_data
    with sensor_data.lock:
        if debug_mode:
            sensor_data.test_tick_data()

        print(
            f"previous_angle {sensor_data.previous_angle} current_angle {sensor_data.current_angle} current_distance {sensor_data.current_distance}"
        )

        if sensor_data.current_distance >= 0:
            sensor_data.update()
        print(
            f"sensor_data.angles {len(sensor_data.angles)} sensor_data.distances {(sensor_data.distances)}"
        )
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

        if sensor_data.current_distance >= 0:
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
                sector=[0, 90],
                radialaxis=dict(visible=True, range=[0, DISTANCE_RANGE]),
            ),
            showlegend=False,
        )

        return fig


@app.callback(
    Output("alert-messages", "children"),
    Input("radar-interval", "n_intervals"),
)
def update_alerts(n_interval):
    global sensor_data

    with sensor_data.lock:

        if sensor_data.current_distance < 0:
            object_detected_msg = "Object out of range"
            object_detected_color = "secondary"
            object_detected_style = {"textDecoration": "line-through", "color": "gray"}
        elif sensor_data.current_distance < WARNING_DISTANCE:
            object_detected_msg = "Warning: Object nearby"
            object_detected_color = "danger"  # red color in Bootstrap
            object_detected_style = {"fontWeight": "bold"}
        else:
            object_detected_msg = "No nearby objects"
            object_detected_color = "secondary"
            object_detected_style = {"color": "gray"}

        # Object detection alert
        # Create all alert components
        alerts = [
            dbc.Alert(
                color=object_detected_color,
                className="fw-bold fs-5",
                children=object_detected_msg,
                style=object_detected_style,
            ),
            dbc.Alert(
                id="motor-speed",
                color="dark",
                className="fw-bold fs-5",
                children=f"Motor speed: {sensor_data.motor_speed} RPM",
            ),
            dbc.Alert(
                id="distance-threshold",
                color="dark",
                className="fw-bold fs-5",
                children=f"Distance threshold: {sensor_data.distance_threshold} cm",
            ),
            dbc.Alert(
                id="max-detection-distance",
                color="dark",
                className="fw-bold fs-5",
                children=f"Max detection: {sensor_data.max_detection_distance} cm",
            ),
            dbc.Alert(
                id="sleep-timeout",
                color="dark",
                className="fw-bold fs-5",
                children=f"Sleep timeout: {sensor_data.sleep_timeout} sec",
            ),
        ]

        return alerts


if __name__ == "__main__":
    app.run_server(debug=True, use_reloader=False)
