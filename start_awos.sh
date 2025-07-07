#!/bin/bash

# Wait for desktop environment to fully load (important for GUI apps)
sleep 10

# Change to project directory 
cd /home/asif/Desktop/unified_creek_awos

# Activate virtual environment
source .venv/bin/activate

# Run the Python script
python awos.py