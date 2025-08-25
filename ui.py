#!/usr/bin/env python
from PySide6.QtCore import (
    QObject, Signal, Slot, Property, QStringListModel, QTimer, QFileSystemWatcher,
    QUrl
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from evdev import InputDevice, list_devices, ecodes
from input_control import InputController
import datetime
import sys
import os


class Bridge(QObject):
    devicesChanged = Signal()
    triggerChanged = Signal()
    latchedChanged = Signal()
    triggerHeldChanged = Signal()
    deviceCountChanged = Signal()
    runningChanged = Signal()
    logAppended = Signal(str)

    def __init__(self):
        super().__init__()
        self._device_model = QStringListModel()
        self.populate_devices()

        self.input_controller = InputController()
        self.input_controller.on_state_change = self.on_state_change

    @Property("QStringList", notify=devicesChanged)
    def deviceModel(self):
        return self._device_model.stringList()

    def populate_devices(self):
        devs = [InputDevice(p) for p in list_devices()]
        display = [f"{d.name} ({d.path})" for d in devs]
        self._device_map = {f"{d.name} ({d.path})": d.path for d in devs}
        self._device_model.setStringList(display)
        self.devicesChanged.emit()

    @Property(str, notify=triggerChanged)
    def trigger(self):
        return getattr(self, "_trigger", "None")

    @Property(str, notify=latchedChanged)
    def latched(self):
        return getattr(self, "_latched", "None")

    @Property(bool, notify=triggerHeldChanged)
    def triggerHeld(self):
        return getattr(self, "_trigger_held", False)

    @Property(int, notify=deviceCountChanged)
    def deviceCount(self):
        return getattr(self, "_device_count", 0)

    @Property(bool, notify=runningChanged)
    def running(self):
        return getattr(self, "_running", False)

    @Slot(str)
    def addDevice(self, display_name: str):
        if display_name in self._device_map:
            p = self._device_map[display_name]
            self.input_controller.add_device(p)
            self.append_log(f"Added device: {display_name}")

    @Slot()
    def clearDevices(self):
        self.input_controller.clear_devices()
        self.append_log("Cleared devices")

    @Slot()
    def start(self):
        try:
            self.input_controller.start()
            self.append_log("Started input controller")
        except Exception as e:
            self.append_log(f"Error starting: {e}")

    @Slot()
    def stop(self):
        self.input_controller.stop()
        self.append_log("Event loop stopped")

    @Slot()
    def beginSetTrigger(self):
        def enable():
            if not getattr(self.input_controller, "running", False):
                self.append_log("Not running")
                return
            self.input_controller.detect_trigger = True
            self.append_log("Detecting trigger...")

        QTimer.singleShot(500, enable)

    @Slot()
    def refreshDevices(self):
        self.populate_devices()
        self.append_log("Refreshed device list")

    def append_log(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        message = f"[{ts}] {text}"
        self.logAppended.emit(message)

    def on_state_change(self, state: dict):
        latched = state.get("latched_keys", [])
        if latched:
            names = [
                ecodes.keys.get(code) or ecodes.BTN.get(code) or str(code)
                for code in latched
            ]
            latched_str = ", ".join(str(x) for x in names)
        else:
            latched_str = "None"

        code = state.get("trigger_code")
        name = (ecodes.keys.get(code) or ecodes.BTN.get(code) or str(code))

        self._latched = latched_str
        self.latchedChanged.emit()

        self._trigger = name
        self.triggerChanged.emit()

        self._trigger_held = bool(state.get("trigger_held", False))
        self.triggerHeldChanged.emit()

        self._device_count = int(state.get("device_count", 0))
        self.deviceCountChanged.emit()

        self._running = bool(state.get("running", False))
        self.runningChanged.emit()

        self.append_log(f"Trigger={state.get('trigger_code')} Latched={latched_str} Held={state.get('trigger_held')}")


def watch_and_reload(engine: QQmlApplicationEngine, qml_path: str, watcher: QFileSystemWatcher):
    """
    Add the qml_path to watcher and connect change events to a debounced reload.
    """
    # ensure absolute path and URL
    qml_path = os.path.abspath(qml_path)
    url = QUrl.fromLocalFile(qml_path)

    # Keep a single-shot timer for debounce
    debounce_timer = QTimer()
    debounce_timer.setSingleShot(True)
    debounce_timer.setInterval(200)  # ms

    def do_reload():
        # delete existing root objects
        for obj in list(engine.rootObjects()):
            obj.deleteLater()
        # clear QML caches and reload
        engine.clearComponentCache()
        engine.load(url)

    def on_file_changed(path):
        # file change events can come in quickly; debounce them
        debounce_timer.start()

    debounce_timer.timeout.connect(do_reload)

    # Add file to watcher (ignore duplicates)
    paths = watcher.files()
    if qml_path not in paths:
        watcher.addPath(qml_path)
    watcher.fileChanged.connect(on_file_changed)


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    bridge = Bridge()
    engine.rootContext().setContextProperty("bridge", bridge)

    qml_file = "main.qml"
    qml_url = QUrl.fromLocalFile(os.path.abspath(qml_file))
    engine.load(qml_url)
    if not engine.rootObjects():
        sys.exit(-1)

    # Setup file watcher for hot reload
    watcher = QFileSystemWatcher()
    watch_and_reload(engine, qml_file, watcher)

    sys.exit(app.exec())