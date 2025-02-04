@echo off
setlocal enabledelayedexpansion

:: Get the directory where the script is located
set "DIR=%~dp0"

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is required but not installed.
    pause
    exit /b 1
)

:: Create and activate virtual environment
set "VENV_DIR=%DIR%..\.venv"
if exist "%VENV_DIR%" (
    echo Using existing virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
    call "%VENV_DIR%\Scripts\activate.bat"
    
    :: Install required packages
    echo Installing required packages...
    python -m pip install --upgrade pip
    if errorlevel 1 (
        echo Error: Failed to upgrade pip.
        pause
        exit /b 1
    )
    pip install -r "%DIR%requirements.txt"
    if errorlevel 1 (
        echo Error: Failed to install requirements.
        pause
        exit /b 1
    )
)

:: Check if credentials exist
if not exist "%DIR%credentials\credentials.json" (
    echo Warning: credentials.json not found in credentials folder.
    echo Please place your Google OAuth credentials file in the credentials folder before proceeding.
    pause
)

:: Create necessary directories
mkdir "%DIR%logs" 2>nul

:: Change to the app directory
cd /d "%DIR%"

:: Run the Streamlit app
echo Starting the application...
streamlit run app.py
if errorlevel 1 (
    echo Error: Failed to start the application.
    pause
    exit /b 1
)

pause 