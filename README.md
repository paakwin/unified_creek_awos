# Unified Creek AWOS

A comprehensive weather station and dashboard system implemented in Python using Tkinter, Modbus RTU, and multi-threading. Displays real-time environmental data and logs it reliably.

## 🌞 Features

### Main Components

- **Full-screen Dashboard** built with Tkinter
- Displays Temperature, Humidity, Pressure, UV Index, AQI, Wind Speed/Direction, and Rainfall
- Supports background images and precise widget positioning

### Sensor Integration

- Uses Modbus RTU for sensor communication (Environment, UV, AQI, Wind, Rain)

### Data Management

- Real-time data collection and display
- CSV logging with daily file rotation and 7-day retention
- State indicators with color coding

### Special Features

- Offline sunrise/sunset times from a CSV file
- Coordinate mapping mode for layout debugging
- Automatic rain gauge reset logic after 12 hours of no significant activity

### Technical Details

- Modbus RTU protocol for sensor connectivity
- Threading for concurrent sensor reading and CSV writing
- INI-based configuration for easy customization
- Keyboard shortcuts:
  - `F5`: Force display refresh
  - `F12`: Toggle coordinate mapping mode
  - `Escape`: Shutdown

## 🚀 Getting Started

1. **Clone the repository**:
   ```bash
   git clone https://github.com/paakwin/unified_creek_awos.git
   cd unified_creek_awos
   ```

2. **Optional: Install Open-Meteo client and AQI helpers** (recommended for AQI/air-quality features):

   Using `uv` (preferred if you use the `uv` package manager):
   ```bash
   uv add openmeteo-requests requests-cache retry-requests
   ```

   Or using `pip`:
   ```bash
   pip install openmeteo-requests requests-cache retry-requests
   ```

3. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

4. **Run the program**:
   ```bash
   uv run python awos.py
   ```

## 🔄 Auto-Start Setup (Linux)

To make AWOS start automatically when you log in:

### 1. Create a startup script

Create a file named `start_awos.sh`:

```bash
#!/bin/bash

# Change to project directory
cd /home/soe/unified_creek_awos

# Activate virtual environment
source .venv/bin/activate

# Run the Python script
python awos.py
```

Make it executable:
```bash
chmod +x /home/soe/unified_creek_awos/start_awos.sh
```

### 2. Create the autostart directory

```bash
mkdir -p ~/.config/autostart
```

### 3. Create the desktop entry file

```bash
cat > ~/.config/autostart/awos.desktop << 'EOF'
[Desktop Entry]
Name=AWOS
Comment=Start AWOS Weather Station
Exec=/home/soe/unified_creek_awos/start_awos.sh
Type=Application
X-GNOME-Autostart-enabled=true
EOF
```

Make it executable:
```bash
chmod +x ~/.config/autostart/awos.desktop
```

### 4. Test the startup script

```bash
/home/soe/unified_creek_awos/start_awos.sh
```

### 5. Verify setup

If everything is set up correctly:
- The script will run automatically when you log in
- The virtual environment will be activated
- The AWOS application will start

To test without rebooting, log out and log back in. The application should start automatically.

If you need to modify the startup behavior, edit the `~/.config/autostart/awos.desktop` file.

## ⚡️ Key Innovations

- Offline sun data for consistent performance
- Color-coded status indicators for quick status assessment
- Thread-safe data handling for reliability
- Automated error recovery and logging

## 🛠️ Contributing

Contributions are welcome! Feel free to open issues or pull requests for improvements.

## 📄 License

MIT License. See `LICENSE` for details.

**Developed by **[**paakwin**](https://github.com/paakwin)

