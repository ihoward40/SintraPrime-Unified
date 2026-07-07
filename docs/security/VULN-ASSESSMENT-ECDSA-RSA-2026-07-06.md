# Vulnerability Assessment — ecdsa and rsa (transitive deps of python-jose)

**Repository:** SintraPrime-Unified  
**Date:** 2026-07-06  
**Affected transitive packages:** `ecdsa`, `rsa`  
**Root direct dependency:** `python-jose>=3.4.0`  

## Findings

1. **No direct dependency declared.** Neither `ecdsa` nor `rsa` is listed in `pyproject.toml`, `requirements.txt`, or `requirements-py313-windows.txt`.
2. **Both come from `python-jose`.** The installed version `python-jose 3.5.0` requires `ecdsa`, `pyasn1`, and `rsa`.
3. **`rsa` alert GHSA-xrx6-fmxq-rjj2 (CVE-2020-25658).** Patched in `rsa>=4.7`. The currently resolved version in this environment is `rsa 4.9.1`, which is **already patched**. Dependabot is flagging a transitive relationship but has not refreshed against the resolved version.
4. **`ecdsa` alert GHSA-wj6h-64fc-37mp (CVE-2024-23342).** The `python-ecdsa` maintainers state: *"The python-ecdsa project considers side channel attacks out of scope for the project and there is no planned fix."* Therefore there is **no patched version available**. The alert is informational and cannot be remediated by a version bump.

## Recommended actions

1. **For `rsa`:** Wait for GitHub Dependabot to re-scan `main` after the `requests>=2.33.0` update is merged. The resolved `rsa 4.9.1` should clear this alert.
2. **For `ecdsa`:** Because no fix exists and the package is only used transitively via `python-jose`, either:
   - Accept the risk and document it (this file), or
   - Replace `python-jose` with a library that does not depend on `python-ecdsa` (e.g., `joserfc` or direct `PyJWT`/`cryptography` usage). This would be a larger refactor requiring ADR and migration of JWT/JWS/JWE code.

## Current mitigation

- `python-jose` is already at the latest version (3.5.0) and uses `ecdsa` only for ECDSA signing/verification, which is not in the hot path of the SintraPrime portal JWT handling (portal uses `PyJWT` for JWT and `python-jose` only where JWS/JWE broader support is needed).
- No code in this repository calls `ecdsa.SigningKey.sign_digest()` or `rsa.decrypt()` directly.

## Decision

Document and defer `ecdsa`. Re-assess after Dependabot re-scan confirms whether the `rsa` alert clears.
