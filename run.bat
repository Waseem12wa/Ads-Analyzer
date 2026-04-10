@echo off
echo ========================================
echo Facebook Ads Library Download Tool
echo ========================================
echo.

echo Checking Python installation...
py --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.13+
    echo Download from: https://www.python.org
    pause
    exit /b 1
)

echo Installing dependencies...
py -m pip install -q -r requirements.txt

if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting Web Interface
echo ========================================
echo.
echo Opening at: http://127.0.0.1:5000
echo Press Ctrl+C to stop
echo.

py app.py

pause
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to PATH
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing dependencies
    pause
    exit /b 1
)

REM Install Playwright browsers
echo Installing Playwright browsers (this may take a few minutes)...
playwright install chromium
if %errorlevel% neq 0 (
    echo Error installing Playwright browsers
    pause
    exit /b 1
)

echo.
echo ====================================
echo Setup Complete!
echo ====================================
echo.
echo Starting backend server on http://localhost:8000
echo.
echo You can now:
echo 1. Open another terminal and run: open_frontend.bat
echo 2. Or manually open: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py
@echo off
echo ============================================================
echo        AD TRACKER - Starting Application
echo ============================================================
echo.

REM Check if Python is installed
REM Try different Python commands
py --version >nul 2>&1
if errorlevel 1 (
    python --version >nul 2>&1
    if errorlevel 1 (
        python3 --version >nul 2>&1
        if errorlevel 1 (
            echo ❌ Python not found. Please install Python first.
            pause
            exit /b 1
        )
    )
)

echo ✅ Python found
echo.

REM Check if dependencies are installed
echo 📦 Checking dependencies...
py -m pip show Flask >nul 2>&1
if errorlevel 1 (
    echo ⚙️  Installing dependencies...
    py -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo ✅ Dependencies ready
echo.
echo 🚀 Starting Ad Tracker API...
echo 📡 Server: http://localhost:5000
echo 🌐 Frontend: http://localhost:5000/
echo.
echo Press Ctrl+C to stop the server
echo.

py api.py
