@echo off
REM Phase 24C: Windows Deployment Start
echo Starting SintraPrime-Unified to C\\SintraPrime-Unified
echo Starting SintraPrime-Unified...
python -m uvicorn portal.main:app --host 0.0.0.0 --port 8000 --reload
pause