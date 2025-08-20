@echo off

echo Luanching MSST WebUI ...

start powershell -Command ".\workenv\python.exe .\webUI.py -i 0.0.0.0"

start powershell -Command ".\workenv\python.exe .\client.py"

echo MSST WebUI is running ...

pause