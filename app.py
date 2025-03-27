import argparse
import asyncio
import bisect
import random
import struct
import threading
from bleak import BleakClient
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import numpy as np
import plotly.graph_objects as go


# CHARACTERISTIC_UUID = "12345678-1234-5678-1234-56789abcdef0"
RX_CHARACTERISTIC_UUID = "abcd1234-5678-1234-5678-abcdef123456"  # Send to ESP32
TX_CHARACTERISTIC_UUID = "dcba4321-8765-4321-8765-654321fedcba"  # Receive from ESP32
DEVICE_ADDRESS = "18:8b:0e:a9:a8:d6"

TEST_ANGLE_INCREMENT = 2.5
UPDATE_INTERVAL = 125.0
WARNING_DISTANCE = 30
DISTANCE_RANGE = 70

# Flag to enable sending data to ESP32
SEND_DATA = False

MOTOR_SPEED = 0
DISTANCE_THRESHOLD = 30
MAX_DETECTION_DISTANCE = 50
SLEEP_TIMEOUT = 10

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
        ) = struct.unpack("ifiiii", data)

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

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SANDSTONE])

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
        html.Hr(),
        html.H4("Device Settings", className="text-center mb-3"),
        
        # Distance Threshold Buttons
        html.Div([
            html.Label("Distance Threshold (cm):  ", className="me-2"),
            dbc.ButtonGroup([
                dbc.Button("10 cm", id="dist-threshold-10", color="secondary", outline=True),
                dbc.Button("30 cm", id="dist-threshold-30", color="secondary", outline=True),
                dbc.Button("50 cm", id="dist-threshold-50", color="secondary", outline=True),
                dbc.Button("100 cm", id="dist-threshold-100", color="secondary", outline=True),
            ], className="mb-3"),
            html.Div(id="selected-dist-threshold", className="text-muted mb-3")
        ]),
        
        # Motor Speed Buttons
        html.Div([
            html.Label("Motor Speed:  ", className="me-2"),
            dbc.ButtonGroup([
                dbc.Button("Normal", id="motor-speed-normal", color="secondary", outline=True),
                dbc.Button("Fast", id="motor-speed-fast", color="secondary", outline=True),
            ], className="mb-3"),
            html.Div(id="selected-motor-speed", className="text-muted mb-3")
        ]),
        
        # Max Detection Distance Buttons
        html.Div([
            html.Label("Max Detection Distance (cm)  :", className="me-2"),
            dbc.ButtonGroup([
                dbc.Button("250 cm", id="max-detect-250", color="secondary", outline=True),
                dbc.Button("400 cm", id="max-detect-400", color="secondary", outline=True),
            ], className="mb-3"),
            html.Div(id="selected-max-detect", className="text-muted mb-3")
        ]),
        
        # Sleep Timeout Buttons
        html.Div([
            html.Label("Sleep Timeout (sec):  ", className="me-2"),
            dbc.ButtonGroup([
                dbc.Button("2 sec", id="sleep-timeout-2", color="secondary", outline=True),
                dbc.Button("5 sec", id="sleep-timeout-5", color="secondary", outline=True),
                dbc.Button("10 sec", id="sleep-timeout-10", color="secondary", outline=True),
                dbc.Button("30 sec", id="sleep-timeout-30", color="secondary", outline=True),
            ], className="mb-3"),
            html.Div(id="selected-sleep-timeout", className="text-muted mb-3")
        ]),
        
        # Update Button
        dbc.Button(
            "Update Device Settings", 
            id="update-settings-btn", 
            color="primary", 
            className="mt-3 w-100"
        ),
        html.Div(id="settings-update-status", className="mt-2 text-center")
    ],
    width=6,
    className="border border-2 border-warning p-3 rounded-3 h-100",
),
            ],
            #className="g-4 h-100",
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

@app.callback(
    [Output(f"selected-{setting}", "children") for setting in 
     ["dist-threshold", "motor-speed", "max-detect", "sleep-timeout"]],
    [Input(f"{setting}-{value}", "n_clicks") for setting, values in [
        ("dist-threshold", [10, 30, 50, 100]),
        ("motor-speed", ["normal", "fast"]),
        ("max-detect", [250, 400]),
        ("sleep-timeout", [2, 5, 10, 30])
    ] for value in values],
    prevent_initial_call=True
)
def update_selected_settings(
    dist_10, dist_30, dist_50, dist_100,
    speed_normal, speed_fast,
    max_250, max_400,
    timeout_2, timeout_5, timeout_10, timeout_30
):
    ctx = dash.callback_context
    if not ctx.triggered:
        return [dash.no_update] * 4
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Distance Threshold
    if button_id.startswith("dist-threshold"):
        value = int(button_id.split("-")[-1])
        return [f"Selected: {value} cm", 
                dash.no_update, dash.no_update, dash.no_update]
    
    # Motor Speed
    elif button_id.startswith("motor-speed"):
        value = button_id.split("-")[-1].capitalize()
        return [dash.no_update, 
                f"Selected: {value}", 
                dash.no_update, dash.no_update]
    
    # Max Detection
    elif button_id.startswith("max-detect"):
        value = int(button_id.split("-")[-1])
        return [dash.no_update, dash.no_update, 
                f"Selected: {value} cm", 
                dash.no_update]
    
    # Sleep Timeout
    elif button_id.startswith("sleep-timeout"):
        value = int(button_id.split("-")[-1])
        return [dash.no_update, dash.no_update, dash.no_update, 
                f"Selected: {value} sec"]
                

# def notification_handler(sender: int, data: bytearray):
#     global sensor_data
#     if len(data) == 24:
        # with sensor_data.lock:
        #     sensor_data.read_data(data)
#     else:
#         print(f"Warning: Received unexpected data length {len(data)} bytes: {data}")

@app.callback(
    [Output("settings-update-status", "children"),
     Output("settings-update-status", "style")],
    Input("update-settings-btn", "n_clicks"),
    [
        State("selected-motor-speed", "children"),
        State("selected-dist-threshold", "children"),
        State("selected-max-detect", "children"),
        State("selected-sleep-timeout", "children")
    ],
    prevent_initial_call=True
)
def update_settings(n_clicks, motor_speed, dist_threshold, max_detect, sleep_timeout):
    global MOTOR_SPEED, DISTANCE_THRESHOLD, MAX_DETECTION_DISTANCE, SLEEP_TIMEOUT, SEND_DATA
    DISTANCE_THRESHOLD = int(dist_threshold.split(": ")[-1].split()[0]) if dist_threshold else 30
    MOTOR_SPEED = 1 if "Fast" in motor_speed else 0 
    MAX_DETECTION_DISTANCE = int(max_detect.split(": ")[-1].split()[0]) if max_detect else 250
    SLEEP_TIMEOUT = int(sleep_timeout.split(": ")[-1].split()[0]) if sleep_timeout else 10

    SEND_DATA = True

    return "Settings updated successfully via Bluetooth!", {"color": "green", "fontWeight": "bold"}


async def ble_client():
    global MOTOR_SPEED, DISTANCE_THRESHOLD, MAX_DETECTION_DISTANCE, SLEEP_TIMEOUT, SEND_DATA
    async with BleakClient(DEVICE_ADDRESS) as client:
        print("Connected to ESP32!")

        # Function to send data
        async def send_data(angle, distance, motor_speed, alarm_threshold):
            # Pack the data into a 16-byte structure (4x 4-byte values)
            tx_data = struct.pack("iiii", angle, distance, motor_speed, alarm_threshold)

            # Send the packed data to ESP32
            await client.write_gatt_char(RX_CHARACTERISTIC_UUID, tx_data, response=True)
            print(f"Sent: Angle={angle}, Distance={distance}, Motor Speed={motor_speed}, Alarm Threshold={alarm_threshold}")

        # Callback function for receiving data
        def notification_handler(sender, data):
            # Unpack received 24-byte structure
            # angle, distance, motor_speed, alarm_threshold, max_distance, sleep_timeout = struct.unpack("ifiiii", data)
            global sensor_data
            if len(data) == 24:
                with sensor_data.lock:
                    sensor_data.read_data(data)
            # print(f"Received: Angle={angle}, Distance={distance:.2f} cm")
            # print(f"Motor Speed={motor_speed}, Alarm Threshold={alarm_threshold}, Max Distance={max_distance}, Sleep Timeout={sleep_timeout}")

        # Subscribe to notifications
        await client.start_notify(TX_CHARACTERISTIC_UUID, notification_handler)

        # Keep running to receive notifications indefinitely
        print("Listening for BLE data...")

        # Loop to check if a key is pressed to send data
        while True:
            if SEND_DATA:
                # Send data to ESP32
                await send_data(MOTOR_SPEED, DISTANCE_THRESHOLD, MAX_DETECTION_DISTANCE, SLEEP_TIMEOUT)
                SEND_DATA = False
            await asyncio.sleep(1)  # Adjust as needed for your needs

def start_bluetooth():
    asyncio.run(ble_client())


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
                mode="markers",
                marker=dict(size=6, color="green"),
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
                color="info",
                className="fw-bold fs-5",
                children=(
                    "System is sleeping" if sensor_data.motor_speed == 2 else "System is Working"
                ),
            ),
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
                children=f"Motor speed mode: {'Normal' if sensor_data.motor_speed == 0 else 'Fast'}",
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
    app.run(debug=True, use_reloader=False)
