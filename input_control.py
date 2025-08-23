#!/usr/bin/env python

import enum
import threading
import evdev
from evdev import UInput, ecodes as e
import time

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

        caps = self.build_keyboard_mouse_capabilities()
        # Create the UInput device
        self.ui = UInput(caps, name="Latcher", version=0x3)

        # GUI callback
        self.on_state_change = None

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

    def stop(self):
        self.running = False
        self.clear_latches()

        for t in self.threads:
            print("Joining input worker thread")
            t.join()

    def clear_latches(self):
        for k in self.latched_keys:
            self.ui.write(e.EV_KEY, k, KEY_UP)
        self.latched_keys.clear()
        self._update_state()
        self.ui.syn()

    def _update_state(self):
        if self.on_state_change:
            state = {
                "latched_keys": list(self.latched_keys),
                "trigger_held": self.trigger_held,
                "trigger_code": self.trigger_code,
                "device_count": len(self.devices),
                "running": self.running,
            }
            self.on_state_change(state)

    def _event_loop(self, device):
        print("Event loop started")

        try:
            try:
                device.grab()
            except Exception:
                pass
            for event in device.read_loop():
                #event = device.read_one()
                if not self.running:
                    print("Exiting event loop")
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
                    self.latched_keys.add(key)
                    self.ui.write(e.EV_KEY, key, KEY_DOWN)
                    self.new_latches.add(key)

                    self._update_state()
                    self.ui.syn()

                if key in self.latched_keys:
                    if self.trigger_held:
                        continue
                    if val == KEY_UP:
                        #print("Unlatching key", e.EV_KEY)
                        self.latched_keys.remove(key)
                        self.ui.write(e.EV_KEY, key, KEY_UP)
                        self._update_state()
                        self.ui.syn()

                else:
                    # pass through normal events
                    #print("Passing through", key, val)
                    self.ui.write_event(event)
                    self.ui.syn()

        except Exception as ex:
            import traceback
            print("Error reading device")
            traceback.print_exc()

        finally:
            try:
                print("Attempting to ungrab device")
                device.ungrab()
            except Exception:
                pass