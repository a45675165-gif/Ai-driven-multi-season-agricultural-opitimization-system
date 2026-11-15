"""Interactive Plotly charts used by the agricultural optimization dashboard."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


GREEN = "#2f6a4b"
GOLD = "#d69e39"
BLUE = "#4d8290"


def _layout(fig, title, y_title=""):
    fig.update_layout(
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        font={"family": "DM Sans, sans-serif", "color": "#20312c"},
        margin={"l": 20, "r": 20, "t": 55, "b": 20},
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.12},
    )
    fig.update_yaxes(title=y_title, gridcolor="#edf1eb", zerolinecolor="#dfe7dc")
    fig.update_xaxes(gridcolor="#edf1eb")
    return fig


def weather_chart(weather: pd.DataFrame):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if weather.empty:
        fig.add_annotation(text="Waiting for real NASA POWER data", showarrow=False)
        return _layout(fig, "Daily climate conditions")
    fig.add_trace(go.Scatter(x=weather.date, y=weather.temperature_c, name="Temperature (°C)", line={"color": GREEN, "width": 2.5}), secondary_y=False)
    fig.add_trace(go.Bar(x=weather.date, y=weather.rainfall_mm, name="Rainfall (mm)", marker_color=GOLD, opacity=.65), secondary_y=True)
    fig.add_trace(go.Scatter(x=weather.date, y=weather.humidity_pct, name="Humidity (%)", line={"color": BLUE, "dash": "dot"}), secondary_y=True)
    fig.update_yaxes(title_text="Temperature (°C)", secondary_y=False, gridcolor="#edf1eb")
    fig.update_yaxes(title_text="Rainfall (mm) / Humidity (%)", secondary_y=True, showgrid=False)
    return _layout(fig, "Daily climate conditions")


def ec_chart(soil_ec, water_ec):
    labels, values, colors = [], [], []
    if soil_ec is not None:
        labels.append("Soil EC"); values.append(soil_ec); colors.append(GREEN)
    if water_ec is not None:
        labels.append("Irrigation-water EC"); values.append(water_ec); colors.append(BLUE)
    fig = go.Figure()
    if labels:
        fig.add_trace(go.Bar(x=labels, y=values, marker_color=colors, text=[f"{v:g} dS/m" for v in values], textposition="outside"))
    else:
        fig.add_annotation(text="Enter a manual EC reading in the farm profile", showarrow=False)
    fig.update_layout(showlegend=False, yaxis_title="Electrical conductivity (dS/m)")
    return _layout(fig, "Manual EC readings")


def irrigation_chart(plans):
    fig = go.Figure()
    names = [p["name"] for p in plans]
    fig.add_trace(go.Bar(name="Estimated depth (mm/week)", x=names, y=[p["depth_mm_week"] for p in plans], marker_color=[GREEN, "#8cad77", GOLD]))
    fig.update_layout(showlegend=False, yaxis_title="Scenario estimate (mm/week)", xaxis_tickangle=-12)
    return _layout(fig, "Weekly irrigation scenario estimates")
