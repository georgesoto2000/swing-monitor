"""TCP client for the swing-monitor ESP32 CSV stream.

Connects to the board's socket server (see firmware/wifi_csv_export) and
runs the read loop in a background thread so Streamlit's main-thread
reruns never block on network I/O. Parsed rows are handed off through a
thread-safe queue for the UI to drain on each rerun.
"""

import queue
import socket
import threading
import time
from typing import Optional

HOST = "192.168.4.1"
PORT = 5005
RECONNECT_DELAY_S = 2


class SwingStream:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.queue: "queue.Queue[dict]" = queue.Queue()
        self.connected = False
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._read_forever()
            except OSError:
                pass
            self.connected = False
            if not self._stop.is_set():
                time.sleep(RECONNECT_DELAY_S)

    def _read_forever(self):
        with socket.create_connection((self.host, self.port), timeout=5) as sock:
            self.connected = True
            sock.settimeout(1.0)
            buf = b""
            while not self._stop.is_set():
                try:
                    chunk = sock.recv(4096)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                buf += chunk
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    row = self._parse(line.decode("utf-8", errors="ignore").strip())
                    if row:
                        self.queue.put(row)

    @staticmethod
    def _parse(line: str) -> Optional[dict]:
        if not line or line.startswith("millis"):
            return None
        parts = line.split(",")
        if len(parts) != 6:
            return None
        millis, kind, x, y, z, w = parts
        try:
            return {
                "millis": int(millis),
                "type": kind,
                "x": float(x),
                "y": float(y),
                "z": float(z),
                "w": float(w) if w else None,
            }
        except ValueError:
            return None
