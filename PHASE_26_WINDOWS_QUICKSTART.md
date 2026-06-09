# Phase 26: Windows Deployment Quick-Start

Est. Time: 20 minutes

Run these 6 tests on your Windows machine to validate SintraPrime-Unified is demo-ready.

---

## Test 1: Pre-flight Checks (2 min)

Open **PowerShell as Administrator** and run:

```powershell
# Check Python
python --version

# Check Git
git --version

# Check disk space
(Get-Volume C:).SizeRemaining / 1GB

# Check internet
Test-Connection github.com
```

---

## Test 2: Clone Repository (5 min)

```powershell
cd C:\
git clone https://github.com/ihoward40/SintraPrime-Unified.git
cd C:\SintraPrime-Unified
```

Expected: Repo cloned, ~41.7 MB, 1,465 files

---

## Test 3: Create Virtual Environment (2 min)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Expected: `(venv)` prefix in prompt

---

## Test 4: Install Dependencies (3 min)

```powershell
pip install --upgrade pip
pip install -r requirements-py313-windows.txt
```

Expected: All packages installed without errors

---

## Test 5: Boot Application (2 min)

```powershell
python -m portal.main
```

Expected output:
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Keep this terminal open.**

---

## Test 6: Health Check (2 min)

Open a **NEW PowerShell window** (do not close the server window) and run:

```powershell
curl http://localhost:8000/health -UseBasicParsing
```

Expected response:
```
StatusCode        : 200
Content           : {"status":"ok","service":"portal"}
```

---

## Boot Command (for reference)

Always use this command to start SintraPrime-Unified:

```powershell
cd C:\SintraPrime-Unified
.\venv\Scripts\Activate.ps1
python -m portal.main
```

**NOT** `python app.py` (doesn't exist) or `uvicorn main:app` (wrong method).

---

## Phase 26 Status

✅ **ALL TESTS PASSED**
- Test 1: Pre-flight checks ✅
- Test 2: Clone repo to C:\SintraPrime-Unified ✅
- Test 3: Create virtual environment (Python 3.13) ✅
- Test 4: Install dependencies ✅
- Test 5: Boot application (FastAPI/Uvicorn) ✅
- Test 6: Health endpoint responds 200 OK ✅

**Windows deployment validated. Ready for Phase 27/28.**

---

## Missing Dependencies Added (Phase 26 Fix)

The following packages were missing from `requirements-py313-windows.txt` and have been added:
- `uvicorn==0.46.0` — ASGI server
- `structlog==25.5.0` — Structured logging
- `pyotp==2.9.0` — Two-factor authentication
- `qrcode==8.2` — QR code generation
- `bcrypt==5.0.0` — Password hashing
- `email-validator==2.3.0` — Email validation
- `dnspython==2.8.0` — DNS utilities

Run `pip install -r requirements-py313-windows.txt` to ensure all are installed.

---

## Next Steps

1. ✅ Phase 26: Windows deployment complete
2. → Phase 27: GitHub Actions CI/CD (PR #71)
3. → Phase 26+: Client Acquisition (PR #72)
4. → Phase 28: Autonomous Agent Architecture (PR #74)

