import asyncio
import struct
import threading
from bleak import BleakClient
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

# Bluetooth constants
CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-1234567890ab"
device_address = "18:8b:0e:a9:a8:d6"
angle = 0  # Default angle
distance = 0  # Default distance

# Initialize the Dash app
app = dash.Dash(__name__)

# Layout for the Dash app
app.layout = html.Div([
    html.H1("Bluetooth Radar Data"),
    dcc.Graph(id="radar-chart", style={"height": "500px"}),
    dcc.Interval(id="interval-component", interval=1000, n_intervals=0)  # Update every second
])

# Define a function to handle Bluetooth notifications
def notification_handler(sender: int, data: bytearray):
    global angle, distance
    if len(data) == 8:
        angle, distance = struct.unpack('if', data)  # 'if' for int (angle) + float (distance)
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

# Start Bluetooth in a separate thread to avoid blocking the main app
bluetooth_thread = threading.Thread(target=start_bluetooth, daemon=True)
bluetooth_thread.start()

# Update the radar chart with new data
@app.callback(
    Output("radar-chart", "figure"),
    Input("interval-component", "n_intervals")
)
def update_radar_chart(n):
    global angle, distance

    # Create a simple radar chart using Plotly
    fig = go.Figure(go.Scatterpolar(
        r=[distance],  # Distance is used as radial value
        theta=[angle],  # Angle is used as the angle
        mode="markers+text",
        marker=dict(size=10, color="green"),
        text=[f"Angle: {angle}, Distance: {distance:.2f} cm"],
        textposition="top center"
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False
    )

    return fig

# Run the Dash app
if __name__ == "__main__":
    app.run_server(debug=True, use_reloader=False)  # use_reloader=False to prevent the app from restarting twice
