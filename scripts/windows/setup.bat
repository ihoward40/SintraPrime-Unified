@echo off
  PHASE 24C: Windows Deployment Setup
  Installs SintraPrime-Unified to C:\SintraPrime-Unified

  setlocal enabledelayedexpansion
  set DEPLOY_DIR=C:\SintraPrime-Unified
  python -m venv venv
  call venv\Scripts\activate.bat
  pip install -e .
  pause
