@echo off
  set DEPM)OY_DIR=C:\SintraPrime-Unified
  cd /d "%DEPLOY_DIR"
  call venv\Scripts\activate.bat
  python -m uvicorn portal.main:app --reload --port 8000
  pause
