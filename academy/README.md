# SintraPrime Intelligence Academy

A deployable training, certification, red-team, and performance-governance layer for SintraPrime-Unified.

## Core Rule
No agent is promoted because it sounds intelligent. Promotion requires verified accuracy, authoritative sourcing, adversarial survival, calibrated confidence, and successful real-world execution.

## What This Package Includes
- Academy charter and certification rules
- Six initial agent academies
- Source authority hierarchy
- Case-study templates and seeded cases
- Knowledge, applied, adversarial, and production exams
- Universal and specialty checklists
- Red-team review protocol
- Machine-readable scorecards
- Certification and suspension logic
- Failure-to-learning conversion workflow
- PowerShell installer
- Python scoring and certification engine

## Install
From PowerShell:

```powershell
Expand-Archive .\SintraPrime-Intelligence-Academy.zip -DestinationPath C:\Temp\SintraPrimeAcademy
Set-ExecutionPolicy -Scope Process Bypass
C:\Temp\SintraPrimeAcademy\SintraPrime-Intelligence-Academy\install_academy.ps1 -SintraPrimeRoot "C:\SintraPrime-Unified"
```

## Run a Score
```powershell
python C:\SintraPrime-Unified\academy\scripts\academy_cli.py score --input C:\SintraPrime-Unified\academy\data\sample_score.json
```

## Certification Thresholds
- 95–100: Elite
- 90–94.99: Certified
- 80–89.99: Restricted Duty
- 70–79.99: Retraining Required
- Below 70: Suspended
- Any critical failure: Immediate review and provisional decertification
