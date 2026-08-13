"""TCP client for the swing-monitor ESP32 CSV stream.

Connects to the board's socket server (see firmware/wifi_csv_export) and
runs the read loop in a background thread so Streamlit's main-thread
reruns never block on network I/O. Parsed rows are handed off through a
thread-safe queue for the UI to drain on each rerun.
"""

import csv
import queue
import socket
import threading
import time
from datetime import datetime
from pathlib import Path

HOST = "192.168.4.1"
PORT = 5005
RECONNECT_DELAY_S = 2
LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"
CSV_FIELDS = ["millis", "type", "x", "y", "z", "w", "time_iso"]


class SwingStream:
    def __init__(self, host: str = HOST, port: int = PORT, log_dir: Path = LOG_DIR):
        self.host = host
        self.port = port
        self.queue: queue.Queue[dict] = queue.Queue()
        self.connected = False
        self.log_path: Path | None = None
        self._log_dir = log_dir
        self._csv_file = None
        self._csv_writer = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._open_log()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._close_log()

    def _open_log(self):
        self._log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self._log_dir / f"live_{timestamp}.csv"
        self._csv_file = self.log_path.open("w", newline="")
        self._csv_writer = csv.DictWriter(self._csv_file, fieldnames=CSV_FIELDS)
        self._csv_writer.writeheader()

    def _close_log(self):
        if self._csv_file:
            self._csv_file.close()
        self._csv_file = None
        self._csv_writer = None

    def _log_row(self, row: dict):
        if not self._csv_writer:
            return
        time_iso = (
            datetime.fromtimestamp(row["time"])
            .astimezone()
            .isoformat(timespec="milliseconds")
        )
        self._csv_writer.writerow(
            {
                "millis": row["millis"],
                "type": row["type"],
                "x": row["x"],
                "y": row["y"],
                "z": row["z"],
                "w": row["w"],
                "time_iso": time_iso,
            }
        )
        self._csv_file.flush()

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
            # The board only knows ms-since-boot, not wall-clock time (it's an
            # isolated AP with no NTP/RTC). Anchor its millis to our own clock
            # at connect time so rows carry real time-of-day without adding
            # network-jitter noise to the device's own sample timing.
            anchor_millis: int | None = None
            anchor_wall: float | None = None
            while not self._stop.is_set():
                try:
                    chunk = sock.recv(4096)
                except TimeoutError:
                    continue
                if not chunk:
                    break
                buf += chunk
                *lines, buf = buf.split(b"\n")
                for line in lines:
                    row = self._parse(line.decode("utf-8", errors="ignore").strip())
                    if row:
                        if anchor_millis is None:
                            anchor_millis = row["millis"]
                            anchor_wall = time.time()
                        row["time"] = (
                            anchor_wall + (row["millis"] - anchor_millis) / 1000.0
                        )
                        self._log_row(row)
                        self.queue.put(row)

    @staticmethod
    def _parse(line: str) -> dict | None:
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
