"""RJoy HTTP server — virtual joystick + tracking server core + PySide6 bridge."""
import configparser
import enum
import html as html_mod
import http.server
import json
import os
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote, unquote

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer

from hid_joystick_linux import Hid_Joystick

SERVE_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rjoy_web")
PROFILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rjoy_profiles")

# ── Command types ─────────────────────────────────────────────────────────────

class CommandType(enum.Enum):
    Button = "button"
    Axis = "axis"


@dataclass
class ButtonCommand:
    index: int
    value: int  # 1 = press, 0 = release


@dataclass
class AxisCommand:
    index: int
    value: float  # normalised [-1.0, 1.0]


@dataclass
class Command:
    command_type: CommandType
    command_value: ButtonCommand | AxisCommand


def _command_from_dict(d: dict) -> Command:
    kind = d.get("type")
    if kind == "button":
        return Command(
            command_type=CommandType.Button,
            command_value=ButtonCommand(index=int(d["index"]), value=int(d["value"])),
        )
    if kind == "axis":
        return Command(
            command_type=CommandType.Axis,
            command_value=AxisCommand(
                index=int(d["index"]),
                value=max(-1.0, min(1.0, float(d["value"]))),
            ),
        )
    raise ValueError(f"Unknown command type: {kind!r}")


# ── Joystick helpers ──────────────────────────────────────────────────────────

def _make_joystick() -> Hid_Joystick:
    j = Hid_Joystick()
    j.open()
    return j


def _apply_joystick_command(joystick: Hid_Joystick, cmd: Command):
    if cmd.command_type is CommandType.Button:
        v = cmd.command_value
        joystick.set_button(v.index, v.value)
    elif cmd.command_type is CommandType.Axis:
        v = cmd.command_value
        joystick.set_axis(v.index, v.value)


# ── HTTP server ───────────────────────────────────────────────────────────────

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


class _TrackingHTTPServer(http.server.HTTPServer):
    def __init__(self, *args, joystick: Hid_Joystick, **kwargs):
        super().__init__(*args, **kwargs)
        self.joystick = joystick
        self.bytes_sent = 0
        self.bytes_received = 0
        self.active_connections = 0
        self.start_time = time.monotonic()
        self._lock = threading.Lock()


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

    def do_GET(self):
        if self.path == "/status":
            self._serve_status()
        elif self.path == "/profiles":
            self._serve_profile_list_html()
        elif self.path.startswith("/profiles/") and self.path.endswith("/render"):
            name = os.path.basename(unquote(self.path[len("/profiles/"):-len("/render")]))
            self._serve_controls_html(name)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == "/joystick":
            self._handle_joystick()
        else:
            self.send_error(404)

    # ── Joystick ──────────────────────────────────────────────────────────────

    def _handle_joystick(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        with self.server._lock:
            self.server.bytes_received += length
        try:
            _apply_joystick_command(self.server.joystick, _command_from_dict(json.loads(body)))
            self.send_response(204)
            self.end_headers()
        except Exception as ex:
            self.send_error(400, str(ex))

    # ── Profiles ──────────────────────────────────────────────────────────────

    def _serve_profile_list_html(self):
        names = sorted(
            f[:-4] for f in os.listdir(PROFILES_DIR) if f.endswith(".ini")
        )
        parts = []
        for i, name in enumerate(names):
            trigger = "load, click" if i == 0 else "click"
            active_cls = " active" if i == 0 else ""
            parts.append(
                f'<button class="profile-btn{active_cls}"'
                f' hx-get="/profiles/{quote(name)}/render"'
                f' hx-target="#controls"'
                f' hx-swap="innerHTML"'
                f' hx-trigger="{trigger}">'
                f'{html_mod.escape(name)}</button>'
            )
        self._send_html("".join(parts))

    def _serve_controls_html(self, name: str):
        path = os.path.join(PROFILES_DIR, name + ".ini")
        if not os.path.isfile(path):
            self.send_error(404)
            return
        cfg = configparser.ConfigParser()
        cfg.read(path)

        _BTN_W,    _BTN_H    = 90, 90
        _SLIDER_W, _SLIDER_H = 280, 44

        items = []
        canvas_w = canvas_h = 0

        for section in cfg.sections():
            btype = cfg[section].get("Type", "").strip()
            label = html_mod.escape(section)
            x = int(cfg[section].get("X", 0))
            y = int(cfg[section].get("Y", 0))

            if btype == "PushButton":
                btn_idx = int(cfg[section].get("Button", 0))
                items.append(
                    f'<button class="joy-btn placed"'
                    f' style="left:{x}px;top:{y}px;width:{_BTN_W}px;height:{_BTN_H}px"'
                    f' onpointerdown="this.setPointerCapture(event.pointerId);this.classList.add(\'active\');postBtn({btn_idx},1)"'
                    f' onpointerup="this.classList.remove(\'active\');postBtn({btn_idx},0)"'
                    f' onpointercancel="this.classList.remove(\'active\');postBtn({btn_idx},0)">'
                    f'{label}</button>'
                )
                canvas_w = max(canvas_w, x + _BTN_W)
                canvas_h = max(canvas_h, y + _BTN_H)

            elif btype == "SpringSlider":
                axis_idx    = int(cfg[section].get("Axis", 0))
                min_val     = float(cfg[section].get("Min", -1))
                max_val     = float(cfg[section].get("Max",  1))
                default_val = float(cfg[section].get("Default", 0))
                default_str = f"{default_val:.3f}"
                items.append(
                    f'<div class="axis-row placed"'
                    f' style="left:{x}px;top:{y}px;width:{_SLIDER_W}px">'
                    f'<span class="axis-label">{label}</span>'
                    f'<input type="range" min="{min_val}" max="{max_val}" step="0.001"'
                    f' value="{default_val}" class="axis-slider spring-slider"'
                    f' data-axis="{axis_idx}" data-default="{default_val}"'
                    f' oninput="postAxis({axis_idx},+this.value);this.nextElementSibling.textContent=(+this.value).toFixed(3)">'
                    f'<span class="axis-val">{default_str}</span>'
                    f'</div>'
                )
                canvas_w = max(canvas_w, x + _SLIDER_W)
                canvas_h = max(canvas_h, y + _SLIDER_H)

            elif btype == "Slider":
                axis_idx    = int(cfg[section].get("Axis", 0))
                min_val     = float(cfg[section].get("Min", -1))
                max_val     = float(cfg[section].get("Max",  1))
                default_val = float(cfg[section].get("Default", 0))
                default_str = f"{default_val:.3f}"
                reset_js = (
                    "(function(b){"
                    "var inp=b.parentElement.querySelector('input[type=range]');"
                    "var d=parseFloat(inp.dataset.default);"
                    "inp.value=d;"
                    "postAxis(parseInt(inp.dataset.axis),d);"
                    "inp.nextElementSibling.textContent=d.toFixed(3);"
                    "})(this)"
                )
                items.append(
                    f'<div class="axis-row placed"'
                    f' style="left:{x}px;top:{y}px;width:{_SLIDER_W}px">'
                    f'<span class="axis-label">{label}</span>'
                    f'<input type="range" min="{min_val}" max="{max_val}" step="0.001"'
                    f' value="{default_val}" class="axis-slider"'
                    f' data-axis="{axis_idx}" data-default="{default_val}"'
                    f' oninput="postAxis({axis_idx},+this.value);this.nextElementSibling.textContent=(+this.value).toFixed(3)">'
                    f'<span class="axis-val">{default_str}</span>'
                    f'<button class="slider-reset-btn" onclick="{reset_js}">&#x21BA;</button>'
                    f'</div>'
                )
                canvas_w = max(canvas_w, x + _SLIDER_W)
                canvas_h = max(canvas_h, y + _BTN_H)

            elif btype == "DualAxis":
                axis_x   = int(cfg[section].get("AxisX", 0))
                axis_y   = int(cfg[section].get("AxisY", 1))
                recenter_raw = cfg[section].get("Recenter", "true").strip().lower()
                recenter = "true" if recenter_raw in ("true", "1", "yes") else "false"
                _JOYSTICK_SIZE = 160
                reset_btn_html = (
                    '<button class="joystick-reset-btn slider-reset-btn">&#x21BA;</button>'
                    if recenter == "false" else ""
                )
                items.append(
                    f'<div class="joystick-widget placed"'
                    f' style="left:{x}px;top:{y}px">'
                    f'<div class="joystick-outer"'
                    f' data-axis-x="{axis_x}" data-axis-y="{axis_y}" data-recenter="{recenter}">'
                    f'<div class="joystick-thumb"></div>'
                    f'</div>'
                    f'{reset_btn_html}'
                    f'</div>'
                )
                widget_w = _JOYSTICK_SIZE + 96 + 6 if recenter == "false" else _JOYSTICK_SIZE
                canvas_w = max(canvas_w, x + widget_w)
                canvas_h = max(canvas_h, y + _JOYSTICK_SIZE)

        self._send_html(
            '<section class="card">'
            '<div class="section-label">CONTROLS</div>'
            f'<div class="controls-canvas" style="width:{canvas_w + 10}px;height:{canvas_h + 10}px">'
            + "".join(items) +
            '</div></section>'
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _send_html(self, fragment: str):
        body = fragment.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_status(self):
        srv = self.server
        uptime = time.monotonic() - srv.start_time
        rows = [
            ("Uptime",      _fmt_uptime(uptime)),
            ("Connections", str(srv.active_connections)),
            ("Sent",        _fmt_bytes(srv.bytes_sent)),
            ("Received",    _fmt_bytes(srv.bytes_received)),
        ]
        self._send_html("".join(
            f'<div class="stat-row">'
            f'<span class="stat-label">{label}</span>'
            f'<span class="stat-val">{val}</span>'
            f'</div>'
            for label, val in rows
        ))

    def log_message(self, fmt, *args):
        pass


# ── Server core ───────────────────────────────────────────────────────────────

class RJoyServer:
    def __init__(self):
        self._httpd: _TrackingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._joystick: Hid_Joystick | None = None

    def start(self, host: str = "0.0.0.0", port: int = 8765):
        if self.running:
            return
        self._joystick = _make_joystick()
        self._httpd = _TrackingHTTPServer((host, int(port)), _Handler, joystick=self._joystick)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
        if self._thread:
            self._thread.join()
            self._thread = None
        if self._httpd:
            self._httpd.server_close()
            self._httpd = None
        if self._joystick:
            self._joystick.close()
            self._joystick = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def uptime(self) -> float:
        return (time.monotonic() - self._httpd.start_time) if self._httpd else 0.0

    @property
    def bytes_sent(self) -> int:
        return self._httpd.bytes_sent if self._httpd else 0

    @property
    def bytes_received(self) -> int:
        return self._httpd.bytes_received if self._httpd else 0

    @property
    def client_count(self) -> int:
        return self._httpd.active_connections if self._httpd else 0


# ── PySide6 bridge ────────────────────────────────────────────────────────────

class RJoyBridge(QObject):
    runningChanged       = Signal()
    clientCountChanged   = Signal()
    uptimeChanged        = Signal()
    bytesSentChanged     = Signal()
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
