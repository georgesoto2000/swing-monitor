"""Live view of the swing-monitor IMU stream.

Join the board's WiFi hotspot ("swing-monitor") first, then run:
    streamlit run app/streamlit_app.py

This connects to the board as a TCP client on 192.168.4.1:5005 — the
same raw CSV feed the firmware's `nc` capture instructions use — so no
firmware changes are needed.
"""

import math
from collections import deque
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st
from swing_metrics import (
    CLUB_LEVER_ARM_M,
    CLUBS,
    estimated_clubhead_speed_mps,
    magnitude,
    peak_sample,
)
from swing_stream import SwingStream

DEFAULT_WINDOW_SAMPLES = 300  # "Auto" view: samples kept on screen per channel
# Deque capacity: generous headroom above 20s at the sensor's ~200Hz report
# rate, so buffers don't drop samples before the widest selectable window
# has a chance to display them.
BUFFER_MAXLEN = 4500
WINDOW_OPTIONS = {
    "Auto": None,
    "5 second": 5,
    "10 second": 10,
    "15 second": 15,
    "20 second": 20,
}

st.set_page_config(page_title="Swing Monitor", layout="wide")

title_col, clock_col = st.columns([2, 1])
title_col.title("Swing Monitor — Live")
clock = clock_col.empty()

if "stream" not in st.session_state:
    st.session_state.stream = SwingStream()
    st.session_state.stream.start()
    st.session_state.buffers = {
        "ACCEL": deque(maxlen=BUFFER_MAXLEN),
        "GYRO": deque(maxlen=BUFFER_MAXLEN),
        "QUAT": deque(maxlen=BUFFER_MAXLEN),
    }

status = st.empty()
session = st.empty()


def _windowed(rows: list[dict], window_s: float | None) -> list[dict]:
    """Trim ``rows`` to the selected rolling window.

    ``window_s`` of None is the "Auto" option — the fixed-count default
    view. A number trims to the last ``window_s`` seconds relative to the
    newest sample's timestamp.
    """
    if window_s is None:
        return rows[-DEFAULT_WINDOW_SAMPLES:]
    if not rows:
        return rows
    cutoff = rows[-1]["time"] - window_s
    return [r for r in rows if r["time"] >= cutoff]


def _trend_chart(rows: list[dict], value_fn, height: int = 150) -> alt.Chart:
    """A small single-line time chart of ``value_fn(row)`` for each row."""
    df = pd.DataFrame(
        {
            "time": [r["time"] for r in rows],
            "value": [value_fn(r) for r in rows],
        }
    )
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return (
        alt.Chart(df)
        .mark_line()
        .encode(
            x=alt.X("time:T", title="time", axis=alt.Axis(format="%H:%M:%S.%L")),
            y=alt.Y("value:Q", title=None),
        )
        .properties(height=height)
    )


@st.fragment(run_every=0.1)
def live_view():
    stream = st.session_state.stream
    buffers = st.session_state.buffers
    if "paused" not in st.session_state:
        st.session_state.paused = False
    paused = st.session_state.paused

    drained = 0
    while not stream.queue.empty():
        row = stream.queue.get_nowait()
        if not paused:
            buffers[row["type"]].append(row)
        drained += 1

    now = datetime.now().astimezone()
    clock.markdown(
        f"<h1 style='text-align:right'>{now.strftime('%H:%M:%S.%f')[:-3]}</h1>",
        unsafe_allow_html=True,
    )

    if paused:
        status.caption("⏸ Paused: graphs frozen, still recording")
    elif stream.connected:
        status.caption(
            f"Connected: {drained} samples streaming"
            if drained
            else "Connected: waiting for data..."
        )
    else:
        status.caption("Not connected: join the swing-monitor WiFi hotspot")

    if stream.log_path:
        session.caption(f"Session name: {stream.log_path.stem}")

    window_col, club_col, pause_col, _spacer = st.columns([1, 1, 1, 3])
    with window_col:
        window_choice = st.selectbox(
            "Rolling window", list(WINDOW_OPTIONS.keys()), key="window_choice"
        )
    with club_col:
        club = st.selectbox("Club", CLUBS, key="club")
    with pause_col:
        button_label = "▶ Resume" if paused else "⏸ Pause"
        if st.button(
            button_label,
            help="Pause all charts on their current view. Data keeps being "
            "received and logged to CSV in the background.",
        ):
            st.session_state.paused = not paused
            st.rerun()
    window_s = WINDOW_OPTIONS[window_choice]
    lever_arm_m = CLUB_LEVER_ARM_M[club]

    swing_tab, raw_tab = st.tabs(["Swing", "Raw"])

    with raw_tab:
        for kind in ["ACCEL", "GYRO", "QUAT"]:
            st.subheader(kind)
            data = _windowed(list(buffers[kind]), window_s)
            if data:
                df = pd.DataFrame(data)[["time", "x", "y", "z"]]
                df["time"] = pd.to_datetime(df["time"], unit="s")
                long_df = df.melt(id_vars="time", var_name="axis", value_name="value")
                # Millisecond-precision axis: short windows would otherwise
                # round to whole seconds and every tick would look the same.
                chart = (
                    alt.Chart(long_df)
                    .mark_line()
                    .encode(
                        x=alt.X(
                            "time:T",
                            title="time",
                            axis=alt.Axis(format="%H:%M:%S.%L"),
                        ),
                        y=alt.Y("value:Q", title=None),
                        color=alt.Color("axis:N", title=None),
                    )
                    .properties(height=200)
                )
                st.altair_chart(chart, use_container_width=True)

    with swing_tab:
        gyro_rows = _windowed(list(buffers["GYRO"]), window_s)
        accel_rows = _windowed(list(buffers["ACCEL"]), window_s)
        gyro_peak = peak_sample(gyro_rows)
        accel_peak = peak_sample(accel_rows)

        st.subheader("Angular Velocity")
        if gyro_peak:
            st.metric(
                "Angular Velocity",
                f"Peak: {math.degrees(gyro_peak.magnitude):.0f} deg/s",
                label_visibility="collapsed",
            )
            chart = _trend_chart(gyro_rows, lambda r: math.degrees(magnitude(r)))
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Angular Velocity", "Peak: —", label_visibility="collapsed")

        st.subheader("Clubhead Speed")
        if gyro_peak:
            speed_mps = estimated_clubhead_speed_mps(gyro_peak.magnitude, lever_arm_m)
            st.metric(
                "Clubhead Speed",
                f"Peak: {speed_mps * 2.23694:.1f} mph",
                label_visibility="collapsed",
            )
            chart = _trend_chart(
                gyro_rows,
                lambda r: magnitude(r) * lever_arm_m * 2.23694,
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Clubhead Speed", "Peak: —", label_visibility="collapsed")

        st.subheader("Acceleration")
        if accel_peak:
            st.metric(
                "Acceleration",
                f"Peak: {accel_peak.magnitude:.1f} m/s²",
                label_visibility="collapsed",
            )
            chart = _trend_chart(accel_rows, magnitude)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Acceleration", "Peak: —", label_visibility="collapsed")


live_view()
