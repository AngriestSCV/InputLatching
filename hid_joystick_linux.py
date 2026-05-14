"""UHID-based HID joystick device."""
import os
import select
import struct
import threading


_UHID_CREATE2  = 11
_UHID_DESTROY  = 1
_UHID_START    = 2
_UHID_STOP     = 3
_UHID_INPUT2   = 12
_UHID_EVT_SIZE = 4376  # sizeof(struct uhid_event) __packed__

_AXIS_USAGES = [0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37]  # X,Y,Z,Rx,Ry,Rz,Slider,Dial


def _build_descriptor(button_count: int, axis_count: int) -> bytes:
    desc = bytearray()
    desc += bytes([0x05, 0x01, 0x09, 0x04, 0xa1, 0x01])  # UsagePage(Desktop), Usage(Joystick), Collection(App)

    if button_count > 0:
        desc += bytes([0x05, 0x09])               # UsagePage(Button)
        desc += bytes([0x19, 0x01])               # UsageMin(1)
        desc += bytes([0x29, button_count])       # UsageMax(N)
        desc += bytes([0x15, 0x00, 0x25, 0x01])  # LogMin(0), LogMax(1)
        desc += bytes([0x95, button_count])       # Count(N)
        desc += bytes([0x75, 0x01])               # Size(1 bit)
        desc += bytes([0x81, 0x02])               # Input(Data,Var,Abs)
        pad = (8 - button_count % 8) % 8
        if pad:
            desc += bytes([0x95, pad, 0x75, 0x01, 0x81, 0x03])  # Count(pad), Size(1), Input(Const)

    if axis_count > 0:
        desc += bytes([0x05, 0x01])  # UsagePage(Desktop)
        for i in range(min(axis_count, len(_AXIS_USAGES))):
            desc += bytes([0x09, _AXIS_USAGES[i]])
        desc += bytes([0x16, 0x01, 0x80])  # LogMin(-32767)
        desc += bytes([0x26, 0xff, 0x7f])  # LogMax(32767)
        desc += bytes([0x95, axis_count])  # Count(N)
        desc += bytes([0x75, 0x10])        # Size(16 bits)
        desc += bytes([0x81, 0x02])        # Input(Data,Var,Abs)

    desc += bytes([0xc0])  # EndCollection
    return bytes(desc)


class Hid_Joystick:
    def __init__(self, buttonCount: int = 32, axisCount: int = 8):
        if not 0 <= buttonCount <= 128:
            raise ValueError(f"buttonCount must be 0-128, got {buttonCount}")
        if not 0 <= axisCount <= len(_AXIS_USAGES):
            raise ValueError(f"axisCount must be 0-{len(_AXIS_USAGES)}, got {axisCount}")

        self._button_count = buttonCount
        self._axis_count   = axisCount
        self._fd: int | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._started = False
        self._buttons = 0
        self._axes    = [0] * axisCount
        self._lock    = threading.Lock()
        self._descriptor = _build_descriptor(buttonCount, axisCount)

    def open(self):
        self._fd = os.open('/dev/uhid', os.O_RDWR | os.O_CLOEXEC)
        self._running = True
        self._thread = threading.Thread(target=self._event_loop, daemon=True)
        self._thread.start()
        self._send_create()

    def close(self):
        self._running = False
        if self._fd is not None:
            try:
                self._send_destroy()
            except OSError:
                pass
            os.close(self._fd)
            self._fd = None

    def set_button(self, button: int, value: int):
        if not 0 <= button < self._button_count:
            return
        with self._lock:
            if value:
                self._buttons |= 1 << button
            else:
                self._buttons &= ~(1 << button)
            self._flush()

    def set_axis(self, axis: int, value: float):
        if not 0 <= axis < self._axis_count:
            return
        with self._lock:
            self._axes[axis] = max(-32767, min(32767, int(value * 32767)))
            self._flush()

    def get_button_count(self) -> int:
        return self._button_count

    def get_axis_count(self) -> int:
        return self._axis_count

    def _flush(self):
        if not self._started or self._fd is None:
            return
        btn_bytes = (self._button_count + 7) // 8
        report  = self._buttons.to_bytes(btn_bytes, 'little')
        report += struct.pack(f'<{self._axis_count}h', *self._axes)
        payload = struct.pack('<H', len(report)) + report
        self._write_event(_UHID_INPUT2, payload)

    def _send_create(self):
        rd   = self._descriptor
        name = b'RJoy Virtual Joystick'
        payload = (
            name.ljust(128, b'\x00') +
            b'\x00' * 64 +
            b'\x00' * 64 +
            struct.pack('<HH', len(rd), 3) +
            struct.pack('<III', 0x045e, 0x028e, 0x0110) +
            struct.pack('<I', 0) +
            rd.ljust(4096, b'\x00')
        )
        self._write_event(_UHID_CREATE2, payload)

    def _send_destroy(self):
        self._write_event(_UHID_DESTROY, b'')

    def _write_event(self, event_type: int, payload: bytes):
        buf = struct.pack('<I', event_type) + payload
        os.write(self._fd, buf.ljust(_UHID_EVT_SIZE, b'\x00')[:_UHID_EVT_SIZE])

    def _event_loop(self):
        while self._running:
            r, _, _ = select.select([self._fd], [], [], 0.5)
            if not r:
                continue
            try:
                data = os.read(self._fd, _UHID_EVT_SIZE)
            except OSError:
                break
            if len(data) >= 4:
                ev = struct.unpack('<I', data[:4])[0]
                if ev == _UHID_START:
                    self._started = True
                elif ev == _UHID_STOP:
                    self._started = False
