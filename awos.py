#!/usr/bin/env python3
import csv
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pymodbus.client import ModbusSerialClient
import time
from datetime import datetime
import logging
import os
import json
import queue
import threading
from collections import deque
import configparser
import math


class WeatherStationSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Station Dashboard")
        
        # Initialize configuration
        self.load_config()
        
        # Initialize data structures
        self.sensor_data = {}
        self.log_buffer = deque(maxlen=self.config['logging']['max_log_entries'])
        self.data_queue = queue.Queue()
        self.last_rain_value = 0
        self.no_rain_counter = 0
        self.rain_reset_threshold = 0.1
        self.rain_reset_time = 12
        
        # Setup logging
        self.setup_logging()
        self.log("Weather Station System Initializing...")
        
        # Setup GUI
        self.setup_gui()
        
        # Initialize Modbus client
        self.modbus_client = ModbusSerialClient(
            port=self.config['modbus']['port'],
            baudrate=self.config['modbus']['baudrate'],
            parity=self.config['modbus']['parity'],
            stopbits=self.config['modbus']['stopbits'],
            timeout=self.config['modbus']['timeout']
        )
        
        # Sensor configurations
        self.sensor_configs = {
            'temperature': {
                'parser': lambda line: float(line.split("Env: ")[1].split("°C")[0]),
                'display_format': lambda value: f"{value:.1f}°C",
                'widget': 'temperature_value',
                'trigger': "Env:"
            },
            'humidity': {
                'parser': lambda line: float(line.split(", ")[1].split("%")[0]),
                'display_format': lambda value: f"{value:.1f}%",
                'widget': 'humidity_value',
                'trigger': "Env:"
            },
            'pressure': {
                'parser': lambda line: float(line.split(", ")[2].split("hPa")[0]),
                'display_format': lambda value: f"{value:.1f} hPa",
                'widget': 'pressure_value',
                'trigger': "Env:"
            },
            'wind_speed': {
                'parser': lambda line: float(line.split("Wind Speed: ")[1].split(" m/s")[0]) * 3.6,
                'display_format': lambda value: f"{value:.1f} km/hr",
                'widget': 'wind_speed_value',
                'trigger': "Wind Speed:"
            },
            'wind_direction': {
                'parser': lambda line: line.split("Wind Direction: ")[1].split("°")[0].strip(),
                'display_format': lambda value: f"{value}°",
                'widget': 'wind_direction_value',
                'trigger': "Wind Direction:"
            },
            'rain': {
                'parser': lambda line: float(line.split("Raw Rainfall Reading: ")[1].split(" mm")[0]),
                'display_format': lambda value: f"{value:.1f} mm",
                'widget': 'rain_value',
                'trigger': "Raw Rainfall Reading:"
            },
            'uv': {
                'parser': lambda line: float(line.split("UV: ")[1]),
                'display_format': lambda value: f"{value:.2f}",
                'widget': 'uv_value',
                'trigger': "UV:"
            },
            'aqi': {
                'parser': lambda line: float(line.split("'pm2_5': ")[1].split(",")[0]),
                'display_format': lambda value: f"{value:.0f}",
                'widget': 'aqi_value',
                'trigger': "AQI Sensor Data:"
            }
        }
        
        # Start threads
        self.running = True
        self.sensor_thread = threading.Thread(target=self.sensor_reader_loop, daemon=True)
        self.csv_thread = threading.Thread(target=self.csv_writer_loop, daemon=True)
        self.sensor_thread.start()
        self.csv_thread.start()
        
        # Start GUI updates
        self.update_display()
        self.update_static_elements()

    def load_config(self):
        """Load configuration from file or set defaults"""
        self.config = {
            'modbus': {
                'port': '/dev/ttyUSB0',
                'baudrate': 9600,
                'parity': 'N',
                'stopbits': 1,
                'timeout': 2
            },
            'sensors': {
                'environment': 1,
                'uv': 2,
                'aqi': 3,
                'wind_speed': 4,
                'wind_direction': 5,
                'rainfall': 6
            },
            'logging': {
                'log_file': 'weather_station.log',
                'max_log_entries': 500,
                'csv_file': 'weather_data.csv',
                'csv_interval': 30  # seconds
            },
            'gui': {
                'update_interval': 1000,  # ms
                'background_image': './images/GUI_Blank_resized.png'
            }
        }
        
        # Try to load from config file
        try:
            config = configparser.ConfigParser()
            config.read('weather_station.ini')
            
            for section in config.sections():
                for key in config[section]:
                    if section in self.config and key in self.config[section]:
                        value = config[section][key].strip('"\'')
                        if isinstance(self.config[section][key], int):
                            self.config[section][key] = int(value)
                        elif isinstance(self.config[section][key], float):
                            self.config[section][key] = float(value)
                        else:
                            self.config[section][key] = value
                            
            # Convert relative paths to absolute
            if not os.path.isabs(self.config['gui']['background_image']):
                self.config['gui']['background_image'] = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    self.config['gui']['background_image']
                )
        except Exception as e:
            self.log(f"Config load error: {e}. Using defaults.", level=logging.WARNING)

    def setup_logging(self):
        """Configure logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=self.config['logging']['log_file'],
            filemode='a'
        )
        self.logger = logging.getLogger('WeatherStation')
        self.log("System initialized")

    def log(self, message, level=logging.INFO):
        """Log message with timestamp"""
        log_entry = f"{datetime.now().isoformat()} - {message}"
        self.log_buffer.append(log_entry)
        self.logger.log(level, message)

    def setup_gui(self):
        """Initialize the graphical user interface"""
        self.root.attributes('-fullscreen', True)
        
        # Main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True)
        
        # Background
        try:
            img = Image.open(self.config['gui']['background_image'])
            img = img.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()), 
                            Image.Resampling.LANCZOS)
            self.bg_image = ImageTk.PhotoImage(img)
            
            self.bg_canvas = tk.Canvas(
                self.main_frame,
                width=self.root.winfo_screenwidth(),
                height=self.root.winfo_screenheight(),
                highlightthickness=0
            )
            self.bg_canvas.pack(fill='both', expand=True)
            self.bg_canvas.create_image(
                self.root.winfo_screenwidth()//2,
                self.root.winfo_screenheight()//2,
                image=self.bg_image,
                anchor='center'
            )
        except Exception as e:
            self.log(f"GUI setup error: {e}", level=logging.ERROR)
            raise

        # Create display elements
        self.create_display_elements()
        
        # Bind Escape key to exit fullscreen
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

    def create_display_elements(self):
        """Create all GUI display elements"""
        self.number_font = ('Digital-7', 50, 'bold')
        
        # Widget configurations
        self.widget_configs = {
            'temperature_value': {
                'size': 100,
                'color': '#FF4500',
                'position': (69, 130),
                'anchor': 'nw'
            },
            'pressure_value': {
                'size': 50,
                'color': '#32CD32',  
                'position': (1700, 600),
                'anchor': 'center'
            },
            'wind_speed_value': {
                'size': 70,
                'color': '#FFD700',
                'position': (1000, 250),
                'anchor': 'center'
            },
            'wind_direction_value': {
                'size': 60,
                'color': '#FFD700',
                'position': (1670, 240),
                'anchor': 'center'
            },
            'rain_value': {
                'size': 60,
                'color': '#00FFFF',
                'position': (1200, 600),
                'anchor': 's'
            },
            'humidity_value': {
                'size': 60,
                'color': '#ADD8E6',
                'position': (558, 480),
                'anchor': 'nw'
            },
            'humidity_state_value': {
                'size': 40,
                'color': '#ADD8E6',
                'position': (550, 575),
                'anchor': 'nw'
            },
            'aqi_value': {
                'size': 60,
                'color': '#00E400',
                'position': (666, 900),
                'anchor': 'sw'
            },
            'aqi_state_value': {
                'size': 60,
                'color': '#00E400',
                'position': (600, 1000),
                'anchor': 'sw'
            },
            'uv_value': {
                'size': 60,
                'color': '#3EA72D',
                'position': (1800, 900),
                'anchor': 'se'
            },
            'uv_state_value': {
                'size': 60,
                'color': '#3EA72D',
                'position': (1800, 1000),
                'anchor': 'se'
            },
            'current_day_value': {
                'size': 50,
                'color': '#FFFFFF',
                'position': (20, 452),
                'anchor': 'nw'
            },
            'current_date_value': {
                'size': 70,
                'color': '#FFFFFF',
                'position': (150, 729),
                'anchor': 'nw'
            },
            'current_month_value': {
                'size': 60,
                'color': '#FFFFFF',
                'position': (120, 813),
                'anchor': 'nw'
            },
            'current_time_value': {
                'size': 60,
                'color': '#FFFFFF',
                'position': (220, 953),
                'anchor': 'n'
            },
            'sunrise_value': {
                'size': 60,
                'color': '#FFD700',
                'position': (1350, 848),
                'anchor': 'ne'
            },
            'sunset_value': {
                'size': 60,
                'color': '#FFA500',
                'position': (1350, 938),
                'anchor': 'ne'
            }
        }
        
        # Create all widgets
        for widget_name, config in self.widget_configs.items():
            setattr(self, widget_name, self.bg_canvas.create_text(
                config['position'],
                text="--",
                font=(self.number_font[0], config['size'], self.number_font[2]),
                fill=config['color'],
                anchor=config['anchor']
            ))

    def sensor_reader_loop(self):
        """Main loop for reading sensors"""
        last_csv_write = 0
        
        while self.running:
            try:
                if not self.modbus_client.connect():
                    self.log("Modbus connection failed", level=logging.ERROR)
                    time.sleep(5)
                    continue
                
                # Read all sensors
                current_data = {'timestamp': datetime.now().isoformat()}
                
                # Read environment sensor
                env_data = self.read_environment_sensor()
                if env_data:
                    current_data.update(env_data)
                    self.log(f"Env: {env_data['temperature']:.1f}°C, {env_data['humidity']:.1f}%, {env_data['pressure']:.1f}hPa")
                
                # Read UV sensor
                uv_data = self.read_uv_sensor()
                if uv_data:
                    current_data.update(uv_data)
                    self.log(f"UV: {uv_data['uv_index']:.2f}")
                
                # Read AQI sensor
                aqi_data = self.read_aqi_sensor()
                if aqi_data:
                    current_data.update(aqi_data)
                    self.log(f"AQI Sensor Data: {aqi_data}")
                
                # Read wind speed
                wind_speed_data = self.read_wind_speed()
                if wind_speed_data:
                    current_data.update(wind_speed_data)
                    self.log(f"Wind Speed: {wind_speed_data['wind_speed']:.1f} m/s")
                
                # Read wind direction
                wind_dir_data = self.read_wind_direction()
                if wind_dir_data:
                    current_data.update(wind_dir_data)
                    self.log(f"Wind Direction: {wind_dir_data['wind_dir_degrees']}° ({wind_dir_data['wind_dir_cardinal']})")
                
                # Read rainfall
                rainfall_data = self.read_rainfall()
                if rainfall_data:
                    current_data.update(rainfall_data)
                    self.log(f"Raw Rainfall Reading: {rainfall_data['rainfall']:.1f} mm")
                
                # Update shared data
                self.sensor_data = current_data
                
                # Write to CSV if interval has passed
                now = time.time()
                if now - last_csv_write >= self.config['logging']['csv_interval']:
                    self.data_queue.put(current_data)
                    last_csv_write = now
                
                time.sleep(1)  # Maintain 1Hz update rate
                
            except Exception as e:
                self.log(f"Sensor read error: {e}", level=logging.ERROR)
                time.sleep(1)

    def read_environment_sensor(self):
        """Read environment sensor (temperature, humidity, pressure)"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0x0000,
                count=3,
                slave=self.config['sensors']['environment']
            )
            
            if result.isError():
                return None
                
            return {
                'temperature': result.registers[0] / 10.0,
                'humidity': result.registers[1] / 10.0,
                'pressure': result.registers[2] / 10.0
            }
        except Exception as e:
            self.log(f"Environment sensor error: {e}", level=logging.ERROR)
            return None

    def read_uv_sensor(self):
        """Read UV sensor"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0x0000,
                count=1,
                slave=self.config['sensors']['uv']
            )
            
            if result.isError():
                return None
                
            return {'uv_index': result.registers[0] / 100.0}
        except Exception as e:
            self.log(f"UV sensor error: {e}", level=logging.ERROR)
            return None

    def read_aqi_sensor(self):
        """Read AQI sensor data"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0x02,
                count=7,
                slave=self.config['sensors']['aqi']
            )
            
            if result.isError():
                return None
                
            return {
                'co2': result.registers[0],
                'formaldehyde': result.registers[1],
                'tvoc': result.registers[2],
                'pm2_5': result.registers[3],
                'pm10': result.registers[4],
                'aqi_temperature': result.registers[5] / 10.0,
                'aqi_humidity': result.registers[6] / 10.0
            }
        except Exception as e:
            self.log(f"AQI sensor error: {e}", level=logging.ERROR)
            return None

    def read_wind_speed(self):
        """Read wind speed sensor"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0x0000,
                count=1,
                slave=self.config['sensors']['wind_speed']
            )
            
            if result.isError():
                return None
                
            return {'wind_speed': result.registers[0] / 10.0}
        except Exception as e:
            self.log(f"Wind speed sensor error: {e}", level=logging.ERROR)
            return None

    def _degrees_to_cardinal(self, degrees):
        """Convert wind direction in degrees to cardinal direction."""
        if degrees is None or not (0 <= degrees <= 360):
            return "Unknown"
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / (360. / len(directions))) % len(directions)
        return directions[index]

    def read_wind_direction(self):
        """Read wind direction sensor"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0x0000,
                count=3,
                slave=self.config['sensors']['wind_direction']
            )
            
            if result.isError():
                return None
                
            reg_0 = result.registers[0]
            reg_2 = result.registers[2]
            avg_value = (reg_0 + reg_2) / 2.0
            wind_dir_degrees = round(avg_value / 10.0)
            
            if 0 <= wind_dir_degrees <= 360:
                return {
                    'wind_dir_degrees': wind_dir_degrees,
                    'wind_dir_cardinal': self._degrees_to_cardinal(wind_dir_degrees)
                }
            return None
        except Exception as e:
            self.log(f"Wind direction sensor error: {e}", level=logging.ERROR)
            return None

    def read_rainfall(self):
        """Read rainfall sensor"""
        try:
            result = self.modbus_client.read_holding_registers(
                address=0,
                count=1,
                slave=self.config['sensors']['rainfall']
            )
            
            if result.isError():
                return None
                
            return {'rainfall': result.registers[0] / 10.0}
        except Exception as e:
            self.log(f"Rainfall sensor error: {e}", level=logging.ERROR)
            return None

    def csv_writer_loop(self):
        """Background thread for writing CSV data"""
        # Initialize CSV file
        with open(self.config['logging']['csv_file'], 'a+') as f:
            if f.tell() == 0:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'temperature', 'humidity', 'pressure', 'uv_index',
                    'co2', 'formaldehyde', 'tvoc', 'pm2_5', 'pm10',
                    'aqi_temperature', 'aqi_humidity',
                    'wind_speed', 'wind_dir_degrees', 'wind_dir_cardinal',
                    'rainfall'
                ])
        
        while self.running:
            try:
                data = self.data_queue.get(timeout=1)
                
                with open(self.config['logging']['csv_file'], 'a') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        data['timestamp'],
                        data.get('temperature', ''),
                        data.get('humidity', ''),
                        data.get('pressure', ''),
                        data.get('uv_index', ''),
                        data.get('co2', ''),
                        data.get('formaldehyde', ''),
                        data.get('tvoc', ''),
                        data.get('pm2_5', ''),
                        data.get('pm10', ''),
                        data.get('aqi_temperature', ''),
                        data.get('aqi_humidity', ''),
                        data.get('wind_speed', ''),
                        data.get('wind_dir_degrees', ''),
                        data.get('wind_dir_cardinal', ''),
                        data.get('rainfall', '')
                    ])
                    
            except queue.Empty:
                continue
            except Exception as e:
                self.log(f"CSV write error: {e}", level=logging.ERROR)

    def get_datetime_info(self):
        """Get current date and time information"""
        now = datetime.now()
        return {
            'day': now.strftime('%A'),
            'date': now.strftime('%d'),
            'month': now.strftime('%B'),
            'time': now.strftime('%H:%M')
        }

    def get_sun_info(self):
        """Get sunrise and sunset times from CSV file"""
        try:
            current_date = datetime.now().strftime('%m-%d')
            
            with open('karachi_sun_data.csv', 'r') as file:
                next(file)
                for line in file:
                    date, sunrise, sunset = line.strip().split(',')
                    if date == current_date:
                        return {
                            'sunrise': sunrise,
                            'sunset': sunset
                        }
            
            return {
                'sunrise': '06:00',
                'sunset': '18:00'
            }
        except Exception as e:
            self.log(f"Error reading sun data: {e}", level=logging.WARNING)
            return {
                'sunrise': '06:00',
                'sunset': '18:00'
            }

    def get_aqi_state(self, aqi):
        """Determine AQI state and color"""
        if 0 <= aqi <= 50:
            return "Good", "#00E400"
        elif 51 <= aqi <= 100:
            return "Moderate", "#FFFF00"
        elif 101 <= aqi <= 150:
            return "Unhealthy", "#FF7E00"
        elif 151 <= aqi <= 200:
            return "Unhealthy", "#FF0000"
        elif 201 <= aqi <= 300:
            return "Very Unhealthy", "#8F3F97"
        else:
            return "Hazardous", "#7E0023"

    def get_uv_state(self, uv):
        """Determine UV state and color"""
        if 0 <= uv <= 2:
            return "Low", "#3EA72D"
        elif 3 <= uv <= 5:
            return "Moderate", "#FFF300"
        elif 6 <= uv <= 7:
            return "High", "#F18B00"
        elif 8 <= uv <= 10:
            return "Very High", "#E53210"
        else:
            return "Extreme", "#B567A4"

    def get_humidity_state(self, humidity):
        """Determine humidity state and color"""
        if 0 <= humidity <= 30:
            return "Low", "#ADD8E6"
        elif 31 <= humidity <= 50:
            return "Normal", "#00FF00"
        elif 51 <= humidity <= 60:
            return "Slightly High", "#FFFF00"
        elif 61 <= humidity <= 70:
            return "High", "#FFA500"
        else:
            return "Very High", "#FF0000"

    def update_static_elements(self):
        """Update date, time and sun information"""
        datetime_info = self.get_datetime_info()
        sun_info = self.get_sun_info()

        self.bg_canvas.itemconfig(self.current_day_value, text=datetime_info['day'])
        self.bg_canvas.itemconfig(self.current_date_value, text=datetime_info['date'])
        self.bg_canvas.itemconfig(self.current_month_value, text=datetime_info['month'])
        self.bg_canvas.itemconfig(self.current_time_value, text=datetime_info['time'])
        
        self.bg_canvas.itemconfig(self.sunrise_value, text=f"↑{sun_info['sunrise']}")
        self.bg_canvas.itemconfig(self.sunset_value, text=f"↓{sun_info['sunset']}")

        self.root.after(60000, self.update_static_elements)

    def update_display(self):
        """Update display using sensor data"""
        # Simplified display update logic
        pass

    def shutdown(self):
        """Cleanup before exiting"""
        self.log("Shutting down system")
        self.running = False
        if hasattr(self, 'sensor_thread'):
            self.sensor_thread.join(timeout=1)
        if hasattr(self, 'csv_thread'):
            self.csv_thread.join(timeout=1)
        if hasattr(self, 'modbus_client'):
            self.modbus_client.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = WeatherStationSystem(root)
    root.mainloop()