@echo off
REM Phase 24C: Windows Deployment Stop
REM Gracefully shuts down SintraPrime-Unified server

echo.
echo Stopping SintraPrime-Unified server...
echo.

tasklist | find /i "python" >nul
if %errorlevel% equ 0 (
    echo Terminating Python processes...
    taskkill /F /IM python.exe >nul 2>&1
    echo Done.
) else (
    echo No Python processes found
)

echo.
pause
