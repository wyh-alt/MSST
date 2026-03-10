@echo off

cd /d "%~dp0"

echo Launching MSST API in a new window ...

start "MSST API" powershell -NoExit -Command ".\workenv\python.exe -m uvicorn msst_api:app --host 0.0.0.0 --port 7862"

echo MSST API is running on http://localhost:7862/ui
pause

