import asyncio
import bisect
import random
import struct
import threading
from bleak import BleakClient
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-1234567890ab"
device_address = "18:8b:0e:a9:a8:d6"
previous_angle = 0
current_angle = 0
current_distance = 0
move_forward = True
angles = []
distances = []

app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.H1("Bluetooth Radar Data"),
        dcc.Graph(id="radar-chart", style={"height": "500px"}),
        dcc.Interval(id="radar-interval", interval=1000, n_intervals=0),
    ]
)


# Define a function to handle Bluetooth notifications
def notification_handler(sender: int, data: bytearray):
    global current_angle, current_distance
    if len(data) == 8:
        current_angle, current_distance = struct.unpack("if", data)
    else:
        print(f"Warning: Received unexpected data length {len(data)} bytes: {data}")


# Bluetooth communication logic
async def bluetooth_run():
    async with BleakClient(device_address) as client:
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
    global previous_angle, current_angle, current_distance, angles, distances

    # TESTING data
    previous_angle = current_angle
    delta_distance = (
        random.randint(-12, 10) if current_distance > 50 else random.randint(-8, 10)
    )
    current_distance = max(0, min(current_distance + delta_distance, 100))
    if move_forward == 1:
        current_angle += 10.0
        if current_angle >= 180.0:
            current_angle = 180.0
    else:
        current_angle -= 10.0
        if current_angle <= 0.0:
            current_angle = 0.0


    print(f"previous_angle {previous_angle} current_angle {current_angle} current_distance {current_distance}")

    # This assumes the angle increases
    print(angles)
    print(distances)
    left_idx = bisect.bisect_left(angles, previous_angle) + 1
    right_idx = bisect.bisect_right(angles, current_angle)
    print(f"left_idx {left_idx} right_idx {right_idx}")
    angles = angles[:left_idx] + angles[right_idx:]
    distances = distances[:left_idx] + distances[right_idx:]
    print(angles)
    print(distances)

    insert_idx = bisect.bisect_left(angles, current_angle)
    angles.insert(insert_idx, current_angle)
    distances.insert(insert_idx, current_distance)

    fig = go.Figure(
        go.Scatterpolar(
            r=distances,
            theta=angles,
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[distances[insert_idx]],
            theta=[angles[insert_idx]],
            mode="markers+text",
            marker=dict(size=8, color="green"),
            text=[f"Angle: {current_angle}, Distance: {current_distance:.2f} cm"],
            textposition="top center",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False
    )

    return fig


# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True, use_reloader=False)
