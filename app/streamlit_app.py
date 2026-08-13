"""Live view of the swing-monitor IMU stream.

Join the board's WiFi hotspot ("swing-monitor") first, then run:
    streamlit run app/streamlit_app.py

This connects to the board as a TCP client on 192.168.4.1:5005 — the
same raw CSV feed the firmware's `nc` capture instructions use — so no
firmware changes are needed.
"""

from collections import deque
from datetime import datetime

import pandas as pd
import streamlit as st
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

    cols = st.columns(3)
    for col, kind in zip(cols, ["ACCEL", "GYRO", "QUAT"]):
        with col:
            st.subheader(kind)
            data = list(buffers[kind])
            if data:
                df = pd.DataFrame(data).set_index("time")[["x", "y", "z"]]
                df.index = pd.to_datetime(df.index, unit="s")
                st.line_chart(df, height=250)


live_view()
