@echo off
SETLOCAL

REM Go to the folder of the script
cd /d %~dp0

REM Check Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python 3 is not installed. Please install it first!
    pause
    exit /b 1
)

REM Create venv if missing
IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
) ELSE (
    echo Virtual environment already exists.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
pip install --upgrade pip

REM Install only missing packages
echo Checking packages from requirements.txt...
FOR /F "usebackq tokens=*" %%p IN ("requirements.txt") DO (
    pip show %%p >nul 2>&1
    IF %ERRORLEVEL% NEQ 0 (
        echo ⬇ Installing %%p...
        pip install %%p
    ) ELSE (
        echo ✔ %%p already installed.
    )
)

REM Launch Streamlit
echo "
    DIFFICULTY MAP

    Program that calculates the difficulty of accessing points on
    a map as a function of altitude, trails and roads.

    Copyright (C) 2025  Emma DELAHAIE

    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions. See LICENSE.txt for details."

echo Launching Streamlit...
streamlit run difficulty_map/app/Main_page.py

pause
ENDLOCAL
