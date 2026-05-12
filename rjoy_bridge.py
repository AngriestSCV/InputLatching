"""RJoy HTTP server — tracking server core + PySide6 bridge."""
import http.server
import os
import threading
import time

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

SERVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rjoy_web")


class _TrackingHTTPServer(http.server.HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bytes_sent = 0
        self.bytes_received = 0
        self.active_connections = 0
        self.start_time = time.monotonic()
        self._lock = threading.Lock()


def _fmt_bytes(n: int) -> str:
    if n < 1024:        return f"{n} B"
    if n < 1_048_576:   return f"{n/1024:.1f} KB"
    return f"{n/1_048_576:.1f} MB"


def _fmt_uptime(secs: float) -> str:
    s = int(secs)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h: return f"{h}h {m}m {s}s"
    if m: return f"{m}m {s}s"
    return f"{s}s"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SERVE_DIR, **kwargs)

    def setup(self):
        super().setup()
        with self.server._lock:
            self.server.active_connections += 1
        orig = self.wfile.write

        def tracked_write(data):
            with self.server._lock:
                self.server.bytes_sent += len(data)
            return orig(data)

        self.wfile.write = tracked_write

    def finish(self):
        super().finish()
        with self.server._lock:
            self.server.active_connections = max(0, self.server.active_connections - 1)

    def handle_one_request(self):
        super().handle_one_request()
        length = int(self.headers.get("Content-Length", 0)) if hasattr(self, "headers") and self.headers else 0
        if length:
            with self.server._lock:
                self.server.bytes_received += length

    def do_GET(self):
        if self.path == "/status":
            self._serve_status()
        else:
            super().do_GET()

    def _serve_status(self):
        srv = self.server
        uptime = time.monotonic() - srv.start_time
        rows = [
            ("Uptime",      _fmt_uptime(uptime)),
            ("Connections", str(srv.active_connections)),
            ("Sent",        _fmt_bytes(srv.bytes_sent)),
            ("Received",    _fmt_bytes(srv.bytes_received)),
        ]
        html_rows = "".join(
            f'<div class="stat-row">'
            f'<span class="stat-label">{label}</span>'
            f'<span class="stat-val">{val}</span>'
            f'</div>'
            for label, val in rows
        )
        body = html_rows.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


class RJoyServer:
    """Threaded HTTP server that serves rjoy_web/ with live stats."""

    def __init__(self):
        self._httpd: _TrackingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._start_time: float | None = None

    def start(self, host: str = "0.0.0.0", port: int = 8765):
        if self.running:
            return
        self._httpd = _TrackingHTTPServer((host, int(port)), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self._start_time = time.monotonic()

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None
        self._thread = None
        self._start_time = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def uptime(self) -> float:
        return (time.monotonic() - self._start_time) if self._start_time else 0.0

    @property
    def bytes_sent(self) -> int:
        return self._httpd.bytes_sent if self._httpd else 0

    @property
    def bytes_received(self) -> int:
        return self._httpd.bytes_received if self._httpd else 0

    @property
    def client_count(self) -> int:
        return self._httpd.active_connections if self._httpd else 0


class RJoyBridge(QObject):
    runningChanged      = Signal()
    clientCountChanged  = Signal()
    uptimeChanged       = Signal()
    bytesSentChanged    = Signal()
    bytesReceivedChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = RJoyServer()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._poll)

    def _poll(self):
        self.runningChanged.emit()
        self.clientCountChanged.emit()
        self.uptimeChanged.emit()
        self.bytesSentChanged.emit()
        self.bytesReceivedChanged.emit()

    @Slot(str, int)
    def startServer(self, host: str, port: int):
        self._server.start(host, port)
        self._timer.start()
        self._poll()

    @Slot()
    def stopServer(self):
        self._server.stop()
        self._timer.stop()
        self._poll()

    @Property(bool, notify=runningChanged)
    def running(self) -> bool:
        return self._server.running

    @Property(int, notify=clientCountChanged)
    def clientCount(self) -> int:
        return self._server.client_count

    @Property(float, notify=uptimeChanged)
    def uptime(self) -> float:
        return self._server.uptime

    @Property(int, notify=bytesSentChanged)
    def bytesSent(self) -> int:
        return self._server.bytes_sent

    @Property(int, notify=bytesReceivedChanged)
    def bytesReceived(self) -> int:
        return self._server.bytes_received
