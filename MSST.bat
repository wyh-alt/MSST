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

REM Parse server port from config file
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

REM Parse client port from client_config.json
set CLIENT_PORT=7861
if exist "client_config.json" (
    for /f "tokens=2 delims=:" %%a in ('findstr /c:"\"client_port\":" "client_config.json"') do (
        set CLIENT_PORT=%%a
        set CLIENT_PORT=!CLIENT_PORT: =!
        set CLIENT_PORT=!CLIENT_PORT:,=!
        set CLIENT_PORT=!CLIENT_PORT:}=!
    )
)
if "!CLIENT_PORT!"=="" set CLIENT_PORT=7861

echo Using server port: !PORT!
echo Using client port: !CLIENT_PORT!

REM Add Windows Firewall rules for LAN access (requires admin, silently skip if not admin)
echo Configuring firewall for LAN access...
netsh advfirewall firewall show rule name="MSST WebUI Server" >nul 2>&1
if !errorlevel! neq 0 (
    netsh advfirewall firewall add rule name="MSST WebUI Server" dir=in action=allow protocol=TCP localport=!PORT! >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Firewall rule added: Server port !PORT!
    ) else (
        echo   [WARN] Could not add firewall rule for port !PORT! (need admin rights)
    )
) else (
    REM Update existing rule in case port changed
    netsh advfirewall firewall set rule name="MSST WebUI Server" new localport=!PORT! >nul 2>&1
    echo   Firewall rule exists: Server port !PORT!
)

netsh advfirewall firewall show rule name="MSST WebUI Client" >nul 2>&1
if !errorlevel! neq 0 (
    netsh advfirewall firewall add rule name="MSST WebUI Client" dir=in action=allow protocol=TCP localport=!CLIENT_PORT! >nul 2>&1
    if !errorlevel! equ 0 (
        echo   Firewall rule added: Client port !CLIENT_PORT!
    ) else (
        echo   [WARN] Could not add firewall rule for port !CLIENT_PORT! (need admin rights)
    )
) else (
    netsh advfirewall firewall set rule name="MSST WebUI Client" new localport=!CLIENT_PORT! >nul 2>&1
    echo   Firewall rule exists: Client port !CLIENT_PORT!
)

REM Start WebUI server
echo Starting WebUI server...
start powershell -Command "cd '%~dp0'; .\workenv\python.exe .\webUI.py -i 0.0.0.0 -p !PORT!"

REM Wait for server to start
echo Waiting for server to start...
timeout /t 5 /nobreak >nul

REM Start client
echo Starting client...
start powershell -Command "cd '%~dp0'; .\workenv\python.exe .\client.py"

REM Get local IP for LAN access hint
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set LOCAL_IP=%%a
    set LOCAL_IP=!LOCAL_IP: =!
)

echo.
echo ========================================
echo MSST WebUI is running...
echo ========================================
echo.
echo Local access:
echo   Server: http://localhost:!PORT!
echo   Client: http://localhost:!CLIENT_PORT!
echo.
if defined LOCAL_IP (
    echo LAN access (other devices):
    echo   Server: http://!LOCAL_IP!:!PORT!
    echo   Client: http://!LOCAL_IP!:!CLIENT_PORT!
    echo.
)
echo Note: Do not close this window, closing will stop the service
echo Press any key to exit...

pause >nul