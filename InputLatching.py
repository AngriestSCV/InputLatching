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
import json
import sys
import os

_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
CONFIG_PATH = os.path.join(_config_home, "input-latching", "devices.json")


class Bridge(QObject):
    devicesChanged = Signal()
    triggerChanged = Signal()
    latchedChanged = Signal()
    triggerHeldChanged = Signal()
    loadedDevicesChanged = Signal()
    runningChanged = Signal()
    logAppended = Signal(str)

    def __init__(self):
        super().__init__()
        self._device_model = QStringListModel()
        self._loaded_devices = []
        self._trigger = "None"
        self._latched = "None"
        self._trigger_held = False
        self._running = False
        self.populate_devices()

        self.input_controller = InputController()
        self.input_controller.on_state_change = self.on_state_change

        QTimer.singleShot(0, self.load_devices)

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
        return self._trigger

    @Property(str, notify=latchedChanged)
    def latched(self):
        return self._latched

    @Property(bool, notify=triggerHeldChanged)
    def triggerHeld(self):
        return self._trigger_held

    @Property("QStringList", notify=loadedDevicesChanged)
    def loadedDevices(self):
        return self._loaded_devices

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._running

    def save_devices(self):
        saved = [{"name": d.name, "phys": d.phys} for d in self.input_controller.devices]
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"devices": saved}, f)

    def load_devices(self):
        if not os.path.exists(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            current = [InputDevice(p) for p in list_devices()]
            lookup = {(d.name, d.phys): d.path for d in current}
            for entry in data.get("devices", []):
                key = (entry["name"], entry["phys"])
                if key in lookup:
                    try:
                        path = lookup[key]
                        self.input_controller.add_device(path)
                        display_name = f"{entry['name']} ({path})"
                        self._loaded_devices.append(display_name)
                        self.loadedDevicesChanged.emit()
                        self.append_log(f"Restored device: {entry['name']}")
                    except Exception as ex:
                        self.append_log(f"Could not restore {entry['name']}: {ex}")
                else:
                    self.append_log(f"Device not found: {entry['name']}")
        except Exception as ex:
            self.append_log(f"Could not load saved devices: {ex}")

    @Slot(str)
    def addDevice(self, display_name: str):
        if display_name in self._device_map:
            p = self._device_map[display_name]
            self.input_controller.add_device(p)
            self._loaded_devices.append(display_name)
            self.loadedDevicesChanged.emit()
            self.append_log(f"Added device: {display_name}")
            self.save_devices()

    @Slot()
    def clearDevices(self):
        self.input_controller.clear_devices()
        self._loaded_devices = []
        self.loadedDevicesChanged.emit()
        self.append_log("Cleared devices")
        self.save_devices()

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

        self._running = bool(state.get("running", False))
        self.runningChanged.emit()

        self.append_log(f"Trigger={state.get('trigger_code')} Latched={latched_str} Held={state.get('trigger_held')}")


def watch_and_reload(engine: QQmlApplicationEngine, qml_path: str, watcher: QFileSystemWatcher, context_props: dict = None):
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
        # clear QML caches and re-register context properties before reload
        engine.clearComponentCache()
        if context_props:
            for name, obj in context_props.items():
                engine.rootContext().setContextProperty(name, obj)
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
    
    if getattr(sys, "frozen", False):
        # PyInstaller bundle: resources are extracted to sys._MEIPASS
        qml_file = os.path.join(sys._MEIPASS, "main.qml")
    else:
        # Dev or Nix install: main.qml lives next to this script
        qml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.qml")

    qml_url = QUrl.fromLocalFile(os.path.abspath(qml_file))
    engine.load(qml_url)
    if not engine.rootObjects():
        sys.exit(-1)

    # Setup file watcher for hot reload
    watcher = QFileSystemWatcher()
    watch_and_reload(engine, qml_file, watcher, {"bridge": bridge})

    sys.exit(app.exec())