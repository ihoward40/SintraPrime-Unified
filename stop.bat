@echo off
REM Phase 24C: Windows Deployment Stop
echo Stopping SintraPrime-Unified...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq*SintraPrime*"
echo Stopped.
pause