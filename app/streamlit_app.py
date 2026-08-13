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

WINDOW_SIZE = 300  # samples kept on screen per channel

st.set_page_config(page_title="Swing Monitor", layout="wide")
st.title("Swing Monitor — Live")

if "stream" not in st.session_state:
    st.session_state.stream = SwingStream()
    st.session_state.stream.start()
    st.session_state.buffers = {
        "ACCEL": deque(maxlen=WINDOW_SIZE),
        "GYRO": deque(maxlen=WINDOW_SIZE),
        "QUAT": deque(maxlen=WINDOW_SIZE),
    }

clock = st.empty()
status = st.empty()


def _fmt_time(epoch_s: float) -> str:
    """Format an epoch-seconds timestamp as local HH:MM:SS.mmm."""
    return datetime.fromtimestamp(epoch_s).astimezone().strftime("%H:%M:%S.%f")[:-3]


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

    drained = 0
    while not stream.queue.empty():
        row = stream.queue.get_nowait()
        buffers[row["type"]].append(row)
        drained += 1

    now = datetime.now().astimezone()
    clock.caption(f"Current time: {now.strftime('%H:%M:%S.%f')[:-3]}")

    if stream.connected:
        status.caption(
            f"connected — +{drained} samples this tick"
            if drained
            else "connected — waiting for data..."
        )
    else:
        status.caption("not connected — join the swing-monitor WiFi hotspot")

    raw_tab, swing_tab = st.tabs(["Raw", "Swing"])

    with raw_tab:
        for kind in ["ACCEL", "GYRO", "QUAT"]:
            st.subheader(kind)
            data = list(buffers[kind])
            if data:
                df = pd.DataFrame(data)[["time", "x", "y", "z"]]
                df["time"] = pd.to_datetime(df["time"], unit="s")
                long_df = df.melt(id_vars="time", var_name="axis", value_name="value")
                # WINDOW_SIZE samples at up to 200Hz is only ~1.5s on
                # screen — the default axis format rounds to whole
                # seconds, so every tick would show the same label.
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
        st.caption(
            "First-pass metrics: peak values over the samples currently on "
            "screen, not yet tied to a detected swing (see the README's "
            "'Swing event detection' project-plan step)."
        )
        club = st.selectbox("Club", CLUBS, key="club")
        lever_arm_m = CLUB_LEVER_ARM_M[club]

        gyro_rows = list(buffers["GYRO"])
        accel_rows = list(buffers["ACCEL"])
        gyro_peak = peak_sample(gyro_rows)
        accel_peak = peak_sample(accel_rows)

        st.subheader("Peak angular velocity")
        if gyro_peak:
            st.metric(
                "Peak angular velocity",
                f"{math.degrees(gyro_peak.magnitude):.0f} deg/s",
                label_visibility="collapsed",
            )
            st.caption(f"at {_fmt_time(gyro_peak.time)}")
            chart = _trend_chart(gyro_rows, lambda r: math.degrees(magnitude(r)))
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Peak angular velocity", "—", label_visibility="collapsed")

        st.subheader("Peak clubhead speed (est.)")
        if gyro_peak:
            speed_mps = estimated_clubhead_speed_mps(gyro_peak.magnitude, lever_arm_m)
            st.metric(
                "Peak clubhead speed (est.)",
                f"{speed_mps * 2.23694:.1f} mph",
                label_visibility="collapsed",
            )
            st.caption(
                f"{speed_mps:.1f} m/s · {club} lever arm {lever_arm_m:.2f}m "
                "(measured PW, extrapolated for others)"
            )
            chart = _trend_chart(
                gyro_rows,
                lambda r: magnitude(r) * lever_arm_m * 2.23694,
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Peak clubhead speed (est.)", "—", label_visibility="collapsed")

        st.subheader("Peak accel spike")
        if accel_peak:
            st.metric(
                "Peak accel spike",
                f"{accel_peak.magnitude:.1f} m/s²",
                label_visibility="collapsed",
            )
            sharp = (
                f"{accel_peak.sharpness:.0f} m/s³"
                if accel_peak.sharpness is not None
                else "n/a"
            )
            st.caption(f"sharpness {sharp} · at {_fmt_time(accel_peak.time)}")
            chart = _trend_chart(accel_rows, magnitude)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.metric("Peak accel spike", "—", label_visibility="collapsed")


live_view()
