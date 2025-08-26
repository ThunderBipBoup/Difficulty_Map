#!/bin/bash

# Go to the folder of the script
cd "$(dirname "$0")"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install it first!"
    exit 1
fi

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install only missing packages
echo "Checking packages from requirements.txt..."
while IFS= read -r package || [ -n "$package" ]; do
    if ! pip show "$package" > /dev/null 2>&1; then
        echo "⬇ Installing $package..."
        pip install "$package"
    else
        echo "✔ $package already installed."
    fi
done < requirements.txt

# Launch Streamlit
echo "Launching Streamlit..."
echo "
    DIFFICULTY MAP

    Program that calculates the difficulty of accessing points on
    a map as a function of altitude, trails and roads.

    Copyright (C) 2025  Emma DELAHAIE

    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions. See LICENSE.txt for details."

streamlit run difficulty_map/app/Main_page.py
