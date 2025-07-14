#!/usr/bin/env python3
import logging
import time
import threading
import os
from datetime import datetime
from pymodbus.client import ModbusSerialClient

# Ensure logs directory exists
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)

# Configure logging to file and console
log_file = os.path.join(
    log_dir, f'debug_modbus_{datetime.now().strftime("%Y-%m-%d")}.log'
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("DebugModbus")


class SensorDebugger:
    def __init__(self):
        # Modbus configuration (match with multi_awos.py)
        self.config = {
            "modbus": {
                "port": "/dev/ttyUSB0",
                "baudrate": 9600,
                "parity": "N",
                "stopbits": 1,
                "timeout": 2,
                "retries": 3,
            },
            "sensors": {
                "environment": 1,
                "uv": 2,
                "aqi": 3,
                "wind_speed": 4,
                "wind_direction": 5,
                "rainfall": 6,
            },
        }
        self.modbus_lock = threading.Lock()
        self.modbus_client = None
        self.running = True
        self.init_modbus()

    def init_modbus(self) -> None:
        """Initialize Modbus serial client with retry logic."""
        self.modbus_client = ModbusSerialClient(
            port=self.config["modbus"]["port"],
            baudrate=self.config["modbus"]["baudrate"],
            parity=self.config["modbus"]["parity"],
            stopbits=self.config["modbus"]["stopbits"],
            timeout=self.config["modbus"]["timeout"],
        )
        logger.info(
            f"Modbus config: port={self.config['modbus']['port']}, baudrate={self.config['modbus']['baudrate']}"
        )
        for attempt in range(self.config["modbus"]["retries"]):
            with self.modbus_lock:
                if self.modbus_client.connect():
                    logger.info("Modbus connection successful")
                    return
                logger.warning(f"Modbus connection attempt {attempt + 1} failed")
                time.sleep(1)
        logger.error("Modbus connection failed after retries")

    def read_environment_sensor(self) -> dict:
        """Read environment sensor data."""
        with self.modbus_lock:
            try:
                logger.info("Attempting to read environment sensor")
                result = self.modbus_client.read_holding_registers(
                    address=0x0000, count=3, slave=self.config["sensors"]["environment"]
                )
                if result.isError():
                    logger.error("Environment sensor read error: Modbus request failed")
                    return {"temperature": 0.0, "humidity": 0.0, "pressure": 0.0}
                data = {
                    "temperature": result.registers[0] / 10.0,
                    "humidity": result.registers[1] / 10.0,
                    "pressure": result.registers[2] / 10.0,
                }
                logger.info(f"Environment sensor data: {data}")
                return data
            except Exception as e:
                logger.error(f"Environment sensor error: {str(e)}")
                return {"temperature": 0.0, "humidity": 0.0, "pressure": 0.0}

    def read_uv_sensor(self) -> dict:
        """Read UV sensor data."""
        with self.modbus_lock:
            try:
                logger.info("Attempting to read UV sensor")
                result = self.modbus_client.read_holding_registers(
                    address=0x0000, count=1, slave=self.config["sensors"]["uv"]
                )
                if result.isError():
                    logger.error("UV sensor read error: Modbus request failed")
                    return {"uv_index": 0.0}
                data = {"uv_index": result.registers[0] / 10.0}
                logger.info(f"UV sensor data: {data}")
                return data
            except Exception as e:
                logger.error(f"UV sensor error: {str(e)}")
                return {"uv_index": 0.0}

    def read_aqi_sensor(self) -> dict:
        """Read AQI sensor data (placeholder, as it uses CSV in multi_awos.py)."""
        try:
            logger.info("Attempting to read AQI sensor (simulated)")
            # Since AQI is read from CSV in multi_awos.py, return placeholder
            data = {"pm2_5": 0.0}
            logger.info(f"AQI sensor data: {data}")
            return data
        except Exception as e:
            logger.error(f"AQI sensor error: {str(e)}")
            return {"pm2_5": 0.0}

    def read_wind_speed(self) -> dict:
        """Read wind speed sensor data."""
        with self.modbus_lock:
            try:
                logger.info("Attempting to read wind speed sensor")
                result = self.modbus_client.read_holding_registers(
                    address=0x0000, count=1, slave=self.config["sensors"]["wind_speed"]
                )
                if result.isError():
                    logger.error("Wind speed sensor read error: Modbus request failed")
                    return {"wind_speed": 0.0}
                data = {"wind_speed": result.registers[0] / 10.0}
                logger.info(f"Wind speed sensor data: {data}")
                return data
            except Exception as e:
                logger.error(f"Wind speed sensor error: {str(e)}")
                return {"wind_speed": 0.0}

    def read_wind_direction(self) -> dict:
        """Read wind direction sensor data."""
        with self.modbus_lock:
            try:
                logger.info("Attempting to read wind direction sensor")
                result = self.modbus_client.read_holding_registers(
                    address=0x0000,
                    count=1,
                    slave=self.config["sensors"]["wind_direction"],
                )
                if result.isError():
                    logger.error(
                        "Wind direction sensor read error: Modbus request failed"
                    )
                    return None
                data = {"wind_direction": result.registers[0]}
                logger.info(f"Wind direction sensor data: {data}")
                return data
            except Exception as e:
                logger.error(f"Wind direction sensor error: {str(e)}")
                return None

    def read_rainfall(self) -> dict:
        """Read rainfall sensor data."""
        with self.modbus_lock:
            try:
                logger.info("Attempting to read rainfall sensor")
                result = self.modbus_client.read_holding_registers(
                    address=0x0000, count=1, slave=self.config["sensors"]["rainfall"]
                )
                if result.isError():
                    logger.error("Rainfall sensor read error: Modbus request failed")
                    return None
                data = {"rainfall": result.registers[0] / 10.0}
                logger.info(f"Rainfall sensor data: {data}")
                return data
            except Exception as e:
                logger.error(f"Rainfall sensor error: {str(e)}")
                return None

    def sensor_reader_loop(self) -> None:
        """Main sensor reading loop for debugging."""
        while self.running:
            try:
                # Check Modbus connection with retries
                with self.modbus_lock:
                    connected = False
                    for attempt in range(self.config["modbus"]["retries"]):
                        if self.modbus_client.connect():
                            logger.info(
                                "Modbus connection successful in sensor_reader_loop"
                            )
                            connected = True
                            break
                        logger.warning(
                            f"Modbus connection attempt {attempt + 1} failed"
                        )
                        time.sleep(1)
                    if not connected:
                        logger.error("Modbus connection failed after retries")
                        time.sleep(5)
                        continue

                current_data = {"timestamp": datetime.now().isoformat()}

                # Read all sensors
                for sensor_name, reader in [
                    ("environment", self.read_environment_sensor),
                    ("uv", self.read_uv_sensor),
                    ("aqi", self.read_aqi_sensor),
                    ("wind_speed", self.read_wind_speed),
                    ("wind_direction", self.read_wind_direction),
                    ("rainfall", self.read_rainfall),
                ]:
                    try:
                        data = reader()
                        if data:
                            current_data.update(data)
                            logger.info(f"{sensor_name} sensor read successful: {data}")
                            print(f"{sensor_name}: {data}")
                        else:
                            logger.warning(f"{sensor_name} sensor returned no data")
                            print(f"{sensor_name}: No data returned")
                    except Exception as e:
                        logger.error(f"Error reading {sensor_name} sensor: {str(e)}")
                        print(f"{sensor_name}: Error - {str(e)}")

                logger.info(f"Full sensor data: {current_data}")
                print(f"Full data: {current_data}")
                time.sleep(2)  # Increased sleep to reduce serial port strain

            except Exception as e:
                logger.error(f"Sensor read loop error: {str(e)}")
                print(f"Sensor read loop error: {str(e)}")
                time.sleep(2)

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.running = False
        with self.modbus_lock:
            if self.modbus_client:
                self.modbus_client.close()
                logger.info("Modbus client closed")


if __name__ == "__main__":
    debugger = SensorDebugger()
    try:
        debugger.sensor_reader_loop()
    except KeyboardInterrupt:
        debugger.shutdown()
        logger.info("Debugging stopped by user")
