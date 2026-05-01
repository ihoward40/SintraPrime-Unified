@echo off
REM Phase 24C: Windows Deployment Setup
echo Installing SintraPrime-Unified to C:\SintraPrime-Unified

if exist C:\SintraPrime-Unified (
    echo Directory exists. Pulling latest...
    cd /d C:\SintraPrime-Unified
    git pull origin main
) else (
    echo Cloning repository...
    git clone https://github.com/ihoward40/SintraPrime-Unified.git C:\SintraPrime-Unified
    cd /d C:\SintraPrime-Unified
)

echo Installing Python dependencies...
pip install -r requirements.txt

echo Setup complete!
pause
