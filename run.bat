@echo off
TITLE Gmail PDF Processor

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed. Please install Docker first.
    echo Visit: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

REM Check if credentials exist
if not exist "credentials\credentials.json" (
    echo credentials.json not found in credentials directory.
    echo Please place your Google OAuth credentials file in the credentials directory.
    pause
    exit /b 1
)

REM Build and run the application
echo Starting Gmail PDF Processor...
docker-compose up --build

REM Keep window open on error
pause 