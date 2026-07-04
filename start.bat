@echo off
title SintraPrime-Unified — IKE Solutions
color 0E

echo ============================================
echo   SINTRAPRIME-UNIFIED — IKE SOLUTIONS
echo   AI Law Firm & Financial Empire Portal
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python environment...
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python venv not found. Run setup first.
    pause
    exit /b 1
)
echo       Python OK.

echo [2/3] Checking database...
if not exist "data\portal.db" (
    echo       Creating database...
    .venv\Scripts\python.exe -c "from sqlalchemy import create_engine; from portal.database import Base; from portal.models import user,client,case,document,billing,message,audit; Base.metadata.create_all(create_engine('sqlite:///./data/portal.db')); print('       Database created.')"
    echo       Seeding initial data...
    .venv\Scripts\python.exe seed_database.py
) else (
    echo       Database OK.
)

echo [3/3] Starting FastAPI portal...
echo.
echo ============================================
echo   PORTAL RUNNING: http://localhost:8000
echo   API Docs:       http://localhost:8000/docs
echo   Recovery API:   http://localhost:8000/api/recovery/health
echo ============================================
echo.
echo Press Ctrl+C to stop.
echo.

call .venv\Scripts\activate.bat
python -m uvicorn portal.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
pause