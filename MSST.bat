@echo off
setlocal enabledelayedexpansion

echo Starting MSST WebUI...

REM Check if config file exists
if not exist "data\webui_config.json" (
    echo [ERROR] Config file not found: data\webui_config.json
    echo Please run config manager or reinstall the program
    pause
    exit /b 1
)

REM Check if Python environment exists
if not exist "workenv\python.exe" (
    echo [ERROR] Python environment not found: workenv\python.exe
    echo Please check if installation is complete
    pause
    exit /b 1
)

REM Check if main Python files exist
if not exist "webUI.py" (
    echo [ERROR] Main program file not found: webUI.py
    pause
    exit /b 1
)

if not exist "client.py" (
    echo [ERROR] Client file not found: client.py
    pause
    exit /b 1
)

REM Parse port from config file
set PORT=7860
for /f "tokens=2 delims=:" %%a in ('findstr /c:"\"port\":" "data\webui_config.json"') do (
    set PORT=%%a
    set PORT=!PORT: =!
    set PORT=!PORT:,=!
    set PORT=!PORT:}=!
)

REM Use default port if empty or 0
if "!PORT!"=="" set PORT=7860
if "!PORT!"=="0" set PORT=7860

echo Using port: !PORT!

REM Start WebUI server
echo Starting WebUI server...
start powershell -Command "cd '%~dp0'; .\workenv\python.exe .\webUI.py -i 0.0.0.0 -p !PORT!"

REM Wait for server to start
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Start client
echo Starting client...
start powershell -Command "cd '%~dp0'; .\workenv\python.exe .\client.py"

echo.
echo ========================================
echo MSST WebUI is running...
echo ========================================
echo Server address: http://localhost:!PORT!
echo Client address: http://localhost:7861
echo.
echo Note: Do not close this window, closing will stop the service
echo Press any key to exit...

pause >nul