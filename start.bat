@echo off
REM Phase 24C: Windows Deployment Start
echo Starting SintraPrime-Unified...
call .venv\Scripts\activate.bat
python -m uvicorn portal.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
pause
