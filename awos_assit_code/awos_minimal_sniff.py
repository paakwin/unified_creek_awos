#!/usr/bin/env python3
import csv
import os
import threading
import time
import logging
import tkinter as tk
from datetime import datetime
from tkinter import ttk


class WeatherStationSystem:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("RS-485 Passive Sniffer")
        self.running = False

        self.setup_logging()
        self.log("Initializing Passive RS-485 Sniffer...")

        self.config = {
            "modbus": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "parity": "N",
                "stopbits": 1,
                "timeout": 0.1,
            },
            "logging": {"log_file": "sniffer.log"},
        }

        self.csv_dir = os.path.join(os.path.dirname(__file__), "csv_data")
        os.makedirs(self.csv_dir, exist_ok=True)

        self.start_sniffer_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

    def setup_logging(self) -> None:
        try:
            os.makedirs("logs", exist_ok=True)
            log_file = os.path.join(
                "logs", f"sniffer_{datetime.now().strftime('%Y-%m-%d')}.log"
            )
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
                handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
            )
            self.logger = logging.getLogger("Sniffer")
        except Exception as e:
            print(f"Failed to set up logging: {e}")
            self.logger = logging.getLogger("FallbackLogger")

    def log(self, msg: str, level=logging.INFO) -> None:
        if hasattr(self, "logger"):
            self.logger.log(level, msg)
        else:
            print(msg)

    def start_sniffer_thread(self):
        self.running = True
        self.sniffer_thread = threading.Thread(
            target=self.sniff_serial_data, daemon=True
        )
        self.sniffer_thread.start()

    def sniff_serial_data(self):
        try:
            import serial

            ser = serial.Serial(
                port=self.config["modbus"]["port"],
                baudrate=self.config["modbus"]["baudrate"],
                parity=self.config["modbus"]["parity"],
                stopbits=self.config["modbus"]["stopbits"],
                timeout=self.config["modbus"]["timeout"],
            )

            csv_path = os.path.join(self.csv_dir, "sniffer_log.csv")
            if not os.path.exists(csv_path):
                with open(csv_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["timestamp", "raw_data_hex"])

            self.log(f"Sniffer started on {self.config['modbus']['port']}")

            buffer = b""
            last_read_time = time.time()

            while self.running:
                byte = ser.read(1)
                if byte:
                    buffer += byte
                    last_read_time = time.time()
                elif buffer and (time.time() - last_read_time) > 0.05:
                    hex_data = buffer.hex()
                    with open(csv_path, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([datetime.now().isoformat(), hex_data])
                    self.log(f"Captured frame: {hex_data}")
                    buffer = b""

            ser.close()
        except Exception as e:
            self.log(f"Sniffer error: {e}", logging.ERROR)

    def shutdown(self, event=None) -> None:
        self.log("Shutting down sniffer")
        self.running = False
        if hasattr(self, "sniffer_thread"):
            self.sniffer_thread.join(timeout=2)
        self.root.quit()


if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.withdraw()  # Hide GUI window if not needed
        app = WeatherStationSystem(root)
        root.mainloop()
    except Exception as e:
        print(f"Critical error: {e}")
