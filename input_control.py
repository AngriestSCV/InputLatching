#!/usr/bin/env python

from _collections_abc import dict_items
import enum
import random
import threading
import evdev
from evdev import UInput, ecodes as e
import time

from auto_clicker import ClickTracker, AutoClickState

KEY_UP = 0
KEY_DOWN = 1
KEY_HELD = 2


class InputController:
    def __init__(self):
        self.devices = []
        self.running = False
        self.detect_trigger  = False

        self.trigger_code = None
        self.latched_keys = set()
        self.trigger_held = False
        self.new_latches = set()
        self.threads = []

        self.key_trackers: dict[int, ClickTracker] = {}
        self.auto_click_states: dict[int, AutoClickState] = {}
        self._auto_click_lock = threading.Lock()

        caps = self.build_keyboard_mouse_capabilities()
        # Create the UInput device
        self.ui = UInput(caps, name="Latcher", version=0x3)

        # GUI callbacks
        self.on_state_change = None
        self.on_log = None

    def build_keyboard_mouse_capabilities(self):
        # collect all KEY_ and BTN_ codes
        key_codes = []
        for name in dir(e):
            if name.startswith("KEY_") or name.startswith("BTN_"):
                val = getattr(e, name)
                if isinstance(val, int):
                    key_codes.append(val)
        key_codes = sorted(set(key_codes))
        key_codes = [ x for x in key_codes if x <= 767 ]

        # REL axes for relative mouse motion + wheels
        rel_codes = [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL]

        # Optional LEDs (caps/num/scroll)
        led_codes = []
        for nm in ("LED_NUML", "LED_CAPSL", "LED_SCROLLL"):
            if hasattr(e, nm):
                led_codes.append(getattr(e, nm))

        # Optional MSC events
        msc_codes = [e.MSC_SCAN] if hasattr(e, "MSC_SCAN") else []

        # If you want an absolute device (touchpad/tablet) you must provide AbsInfo
        # Here is an example ABS_X/ABS_Y with a common range; comment out if not needed.
        abs_entries = [
            # (code, AbsInfo(min, max, fuzz, flat, resolution))
            # (e.ABS_X, AbsInfo(0, 32767, 0, 0, 0)),
            # (e.ABS_Y, AbsInfo(0, 32767, 0, 0, 0)),
        ]

        caps = {
            e.EV_KEY: key_codes,
            e.EV_REL: rel_codes,
        }
        if led_codes:
            caps[e.EV_LED] = led_codes
        if msc_codes:
            caps[e.EV_MSC] = msc_codes
        if abs_entries:
            caps[e.EV_ABS] = abs_entries

        return caps

    def add_device(self, path):
        dev = evdev.InputDevice(path)
        self.devices.append(dev)
        self._update_state()

    def clear_devices(self):
        self.stop()
        self.devices.clear()

    def start(self):
        if len(self.devices) == 0:
            raise RuntimeError("No input device selected.")

        self.running = True
        for d in self.devices:
            threading.Thread(target=self._event_loop, daemon=True, args=[d]).start()
        threading.Thread(target=self._auto_click_loop, daemon=True).start()

    def stop(self):
        self.running = False
        self.clear_latches()

        for t in self.threads:
            self._log("Joining input worker thread")
            t.join()

    def clear_latches(self):
        for k in self.latched_keys:
            self.ui.write(e.EV_KEY, k, KEY_UP)
        self.latched_keys.clear()
        with self._auto_click_lock:
            for k, state in self.auto_click_states.items():
                if state.holding:
                    self.ui.write(e.EV_KEY, k, KEY_UP)
            self.auto_click_states.clear()
        self.key_trackers.clear()
        self._update_state()
        self.ui.syn()

    def _log(self, msg):
        if self.on_log:
            self.on_log(msg)

    def _update_state(self):
        if self.on_state_change:
            with self._auto_click_lock:
                auto_keys: list[tuple[int, AutoClickState]] = list(self.auto_click_states.items())
            state = {
                "latched_keys": list(self.latched_keys),
                "trigger_held": self.trigger_held,
                "trigger_code": self.trigger_code,
                "device_count": len(self.devices),
                "running": self.running,
                "auto_click_keys": auto_keys,
            }
            self.on_state_change(state)

    def _start_auto_click(self, key, pattern, now):
        ac_state = AutoClickState(pattern=pattern).activate(now, random.gauss(0, 1))
        with self._auto_click_lock:
            self.auto_click_states[key] = ac_state
        self._log(f"Auto-clicking key {key} every ~{pattern.mean_interval:.3f}s")

    def _auto_click_loop(self):
        while self.running:
            now = time.monotonic()
            to_press = []
            to_release = []
            with self._auto_click_lock:
                for key, state in list(self.auto_click_states.items()):
                    new_state, should_press, should_release = state.tick(
                        now, random.gauss(0, 1), random.gauss(0, 1)
                    )
                    self.auto_click_states[key] = new_state
                    if should_press:
                        to_press.append(key)
                    if should_release:
                        to_release.append(key)
            for key in to_release:
                self.ui.write(e.EV_KEY, key, KEY_UP)
            for key in to_press:
                self.ui.write(e.EV_KEY, key, KEY_DOWN)
            if to_press or to_release:
                self.ui.syn()
            time.sleep(0.005)

    def _event_loop(self, device):
        self._log("Event loop started")

        try:
            try:
                device.grab()
            except Exception:
                pass
            for event in device.read_loop():
                #event = device.read_one()
                if not self.running:
                    self._log("Exiting event loop")
                    break
                if event is None:
                    continue

                if event.type != e.EV_KEY:
                    # forward non-key events (mouse motion, scroll, etc.)
                    self.ui.write_event(event)
                    self.ui.syn()
                    continue

                key = event.code
                val = event.value  # 0=up, 1=down, 2=hold

                if self.detect_trigger:
                    if val == KEY_DOWN:
                        self.trigger_code = key
                        self._update_state()
                        self.detect_trigger = False

                # --- Trigger handling ---
                elif key == self.trigger_code:
                    if val == KEY_DOWN:
                        self.trigger_held = True
                        self.new_latches.clear()
                    elif val == KEY_UP:
                        self.trigger_held = False
                        if len(self.new_latches) == 0:
                            self.clear_latches()
                    elif val == KEY_HELD:
                        continue

                    self._update_state()

                # --- Latching logic ---
                elif self.trigger_held and val == KEY_DOWN:
                    tracker = self.key_trackers.get(key, ClickTracker())
                    self.key_trackers[key] = tracker.record_down(time.monotonic())

                    if key not in self.latched_keys and key not in self.auto_click_states:
                        # First press: latch
                        self.latched_keys.add(key)
                        self.ui.write(e.EV_KEY, key, KEY_DOWN)
                        self.new_latches.add(key)
                        self._update_state()
                        self.ui.syn()
                    # 2nd/3rd+ press on already-latched key: down recorded, wait for KEY_UP

                if key in self.latched_keys:
                    if self.trigger_held:
                        if val == KEY_UP and key in self.key_trackers:
                            tracker = self.key_trackers[key]
                            tracker, pattern = tracker.record_up(time.monotonic())
                            self.key_trackers[key] = tracker
                            if pattern is not None:
                                # Triple-click: upgrade latch → auto-click
                                self.latched_keys.remove(key)
                                self.ui.write(e.EV_KEY, key, KEY_UP)
                                self._start_auto_click(key, pattern, time.monotonic())
                                self.new_latches.add(key)
                                self._update_state()
                                self.ui.syn()
                        continue
                    if val == KEY_UP:
                        #print("Unlatching key", e.EV_KEY)
                        self.latched_keys.remove(key)
                        self.ui.write(e.EV_KEY, key, KEY_UP)
                        self._update_state()
                        self.ui.syn()

                elif key in self.auto_click_states:
                    continue  # swallow real events for auto-clicking keys

                else:
                    # pass through normal events
                    #print("Passing through", key, val)
                    self.ui.write_event(event)
                    self.ui.syn()

        except Exception as ex:
            import traceback
            self._log("Error reading device: " + traceback.format_exc())

        finally:
            try:
                self._log("Attempting to ungrab device")
                device.ungrab()
            except Exception:
                pass