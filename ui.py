#!/usr/bin/env python

import tkinter as tk
from tkinter import ttk
from evdev import ecodes, InputDevice, list_devices
from input_control import InputController
import threading
import datetime
import time


class LatchUI:
    def __init__(self, root):
        self.input_controller = InputController()
        self.input_controller.on_state_change = self.update_state

        self.setting_trigger = False  # are we waiting for user to press trigger key?

        root.title("Latch Input Tool")
        root.geometry("500x650")

        # Build mapping: display string -> path
        self.devices = [InputDevice(path) for path in list_devices()]
        self.device_map = {f"{dev.name} ({dev.path})": dev.path for dev in self.devices}

        # Dropdown for devices
        self.device_var = tk.StringVar()
        self.device_menu = ttk.Combobox(
            root,
            textvariable=self.device_var,
            values=list(self.device_map.keys()),
            width=60
        )
        self.device_menu.pack(pady=5)

        self.set_dev_btn = tk.Button(root, text="Add Device", command=self.add_device)
        self.set_dev_btn.pack(pady=5)

        self.set_dev_btn = tk.Button(root, text="Clear Devices", command=self.clear_devices)
        self.set_dev_btn.pack(pady=5)

        # Control buttons
        self.start_btn = tk.Button(root, text="Start", command=self.start)
        self.start_btn.pack(pady=5)

        self.stop_btn = tk.Button(root, text="Stop", command=self.stop)
        self.stop_btn.pack(pady=5)

        self.set_trigger_btn = tk.Button(root, text="Set Trigger", command=self.begin_set_trigger)
        self.set_trigger_btn.pack(pady=5)

        # State labels
        self.trigger_label = tk.Label(root, text="Trigger: None")
        self.trigger_label.pack(pady=5)

        self.latched_label = tk.Label(root, text="Latched: None")
        self.latched_label.pack(pady=5)

        self.state_label = tk.Label(root, text="Trigger Held: False")
        self.state_label.pack(pady=5)

        self.device_count_label = tk.Label(root, text="Devices: ")
        self.device_count_label.pack(pady=5)

        self.running_label = tk.Label(root, text="Running: ")
        self.running_label.pack(pady=5)

        # Logging area
        log_frame = tk.LabelFrame(root, text="Log")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.clear_log_btn = tk.Button(root, text="Clear log", command=self.clear_log)
        self.clear_log_btn.pack(pady=5)

    def log(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def add_device(self):
        dev_display = self.device_var.get()
        if dev_display in self.device_map:
            path = self.device_map[dev_display]
            self.input_controller.add_device(path)
            self.log(f"Added device: {dev_display}")

    def clear_devices(self):
        self.input_controller.clear_devices()

    def start(self):
        try:
            self.input_controller.start()
        except Exception as e:
            self.log(f"Error starting: {e}")

    def stop(self):
        self.input_controller.stop()
        self.log("Event loop stopped")

    def begin_set_trigger(self):
        """Enable trigger capture mode."""
        time.sleep(0.5)
        if not self.input_controller.running:
            self.log("Not running")
            return
        self.input_controller.detect_trigger = True

    def update_state(self, state):
        latched = state["latched_keys"]
        if len(latched) > 0:
            names = [
                ecodes.keys.get(code) or ecodes.BTN.get(code) or str(code)
                for code in latched
            ]
            latched_str = ", ".join([ str(x) for x in names ])
        else:
            latched_str = "None"

        self.latched_label.config(text=f"Latched: {latched_str}")
        self.state_label.config(text=f"Trigger Held: {state['trigger_held']}")

        code = state['trigger_code']
        name = (ecodes.keys.get(code) or
                ecodes.BTN.get(code) or
                str(code))
        self.trigger_label.config(text=f"Trigger: {name}")
        self.device_count_label.config(text=f"Devices: {state['device_count']}")
        self.running_label.config(text=f"Running: {state['running']}")

        self.log(f"Trigger={state['trigger_code']} Latched={latched_str} Held={state['trigger_held']}")



if __name__ == "__main__":
    root = tk.Tk()
    app = LatchUI(root)
    root.mainloop()
