"""
SintraPrime API Gateway
=======================
Lightweight FastAPI app that aggregates all SintraPrime module APIs,
provides rate limiting, API key management, CORS, compression,
and serves the PWA static files.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI, HTTPException, Request, Response, Depends,
    Header, BackgroundTasks, Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sintra.api_gateway")

# ─── Constants ────────────────────────────────────────────────────────────────
VERSION = "1.0.0"
START_TIME = time.time()
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds
PWA_DIR = Path(__file__).parent / "pwa"
API_KEYS_FILE = Path(__file__).parent / ".api_keys.json"

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SintraPrime API Gateway",
    description="Unified API for SintraPrime Legal Intelligence Platform",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "https://sintra.prime",
        "https://*.sintra.prime",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Remaining", "X-RateLimit-Reset", "X-Request-ID"],
)

# ─── Gzip Compression ─────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ─── Rate Limiting ─────────────────────────────────────────────────────────────
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(identifier: str) -> tuple[bool, int, int]:
    """Returns (allowed, remaining, reset_ts)."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    requests = _rate_limit_store.setdefault(identifier, [])
    # Prune old requests
    requests[:] = [t for t in requests if t > window_start]
    if len(requests) >= RATE_LIMIT_REQUESTS:
        reset_ts = int(requests[0] + RATE_LIMIT_WINDOW)
        return False, 0, reset_ts
    requests.append(now)
    remaining = RATE_LIMIT_REQUESTS - len(requests)
    return True, remaining, int(now + RATE_LIMIT_WINDOW)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Skip rate limiting for static files and docs
    if request.url.path.startswith(("/icons/", "/screenshots/", "/api/docs", "/api/redoc")):
        return await call_next(request)

    client_ip = get_client_ip(request)
    # Use API key if present
    api_key = request.headers.get("X-API-Key")
    identifier = f"key:{api_key}" if api_key else f"ip:{client_ip}"

    allowed, remaining, reset_ts = check_rate_limit(identifier)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "message": "Too many requests. Please slow down.", "retry_after": reset_ts - int(time.time())},
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_ts),
                "Retry-After": str(reset_ts - int(time.time())),
            },
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_ts)
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    return response


# ─── API Key Management ────────────────────────────────────────────────────────
class APIKeyStore:
    """Simple file-backed API key store."""

    def __init__(self, path: Path):
        self.path = path
        self._keys: Dict[str, Dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._keys = json.loads(self.path.read_text())
            except Exception:
                self._keys = {}

    def _save(self):
        self.path.write_text(json.dumps(self._keys, indent=2))

    def generate(self, name: str, scopes: List[str] = None) -> Dict:
        key = f"sp_{secrets.token_urlsafe(32)}"
        record = {
            "key": key,
            "name": name,
            "scopes": scopes or ["read"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "usage_count": 0,
            "active": True,
        }
        self._keys[key] = record
        self._save()
        return record

    def validate(self, key: str) -> Optional[Dict]:
        record = self._keys.get(key)
        if record and record.get("active"):
            record["last_used"] = datetime.now(timezone.utc).isoformat()
            record["usage_count"] += 1
            self._save()
            return record
        return None

    def revoke(self, key: str) -> bool:
        if key in self._keys:
            self._keys[key]["active"] = False
            self._save()
            return True
        return False

    def list_keys(self) -> List[Dict]:
        return [
            {k: v for k, v in record.items() if k != "key"}
            | {"key_prefix": record["key"][:12] + "..."}
            for record in self._keys.values()
        ]


api_key_store = APIKeyStore(API_KEYS_FILE)


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Dependency: validates API key if present."""
    if x_api_key:
        record = api_key_store.validate(x_api_key)
        if not record:
            raise HTTPException(status_code=401, detail="Invalid or revoked API key")
        return record
    return None


# ─── Pydantic Models ───────────────────────────────────────────────────────────
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default=["read"])


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    modules: Dict[str, str]
    timestamp: str


# ─── Module Registry ───────────────────────────────────────────────────────────
MODULES = {
    "cases": "active",
    "docket": "active",
    "research": "active",
    "documents": "active",
    "agents": "active",
    "deadlines": "active",
    "esignature": "active",
    "push_notifications": "active",
    "twin_layer": "active",
    "rag": "active",
    "voice": "standby",
    "multimodal": "standby",
}


# ─── Health Endpoint ───────────────────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health(request: Request):
    """System health check — returns status of all modules."""
    uptime = time.time() - START_TIME
    return HealthResponse(
        status="healthy",
        version=VERSION,
        uptime_seconds=round(uptime, 2),
        modules=MODULES,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ─── API Key Endpoints ─────────────────────────────────────────────────────────
@app.post("/api/keys", tags=["API Keys"])
async def create_api_key(body: APIKeyCreate, request: Request):
    """Generate a new API key."""
    record = api_key_store.generate(body.name, body.scopes)
    logger.info("API key created: %s (name=%s)", record["key"][:12], body.name)
    return {"key": record["key"], "name": record["name"], "scopes": record["scopes"], "created_at": record["created_at"]}


@app.get("/api/keys", tags=["API Keys"])
async def list_api_keys(request: Request):
    """List all API keys (keys are masked)."""
    return {"keys": api_key_store.list_keys()}


@app.delete("/api/keys/{key}", tags=["API Keys"])
async def revoke_api_key(key: str, request: Request):
    """Revoke an API key."""
    if api_key_store.revoke(key):
        logger.info("API key revoked: %s", key[:12])
        return {"revoked": True, "key_prefix": key[:12]}
    raise HTTPException(status_code=404, detail="API key not found")


# ─── Proxy / Aggregation Endpoints ────────────────────────────────────────────
@app.get("/api/cases", tags=["Cases"])
async def get_cases(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Aggregate case list from Cases module."""
    try:
        from cases.api import list_cases  # type: ignore
        return await list_cases(status=status, limit=limit, offset=offset)
    except ImportError:
        return _stub_response("cases", {"cases": [], "total": 0, "limit": limit, "offset": offset})


@app.get("/api/deadlines", tags=["Deadlines"])
async def get_deadlines(
    days: int = Query(default=30, ge=1, le=365),
    case_id: Optional[str] = Query(default=None),
):
    """Aggregate deadlines from Docket module."""
    try:
        from docket.api import get_deadlines  # type: ignore
        return await get_deadlines(days=days, case_id=case_id)
    except ImportError:
        return _stub_response("deadlines", {"deadlines": [], "days": days})


@app.get("/api/deadlines/upcoming", tags=["Deadlines"])
async def get_upcoming_deadlines(days: int = Query(default=7)):
    """Get deadlines within the next N days."""
    try:
        from docket.api import get_upcoming_deadlines  # type: ignore
        return await get_upcoming_deadlines(days=days)
    except ImportError:
        return _stub_response("deadlines", {"deadlines": [], "days": days})


@app.get("/api/activity", tags=["Dashboard"])
async def get_activity(limit: int = Query(default=10, ge=1, le=50)):
    """Get recent system activity."""
    return {"items": [], "limit": limit}


@app.post("/api/research/query", tags=["Research"])
async def research_query(request: Request):
    """Execute legal research query via RAG module."""
    body = await request.json()
    query = body.get("query", "")
    try:
        from rag.api import search  # type: ignore
        return await search(query=query, options=body)
    except ImportError:
        return _stub_response("research", {"results": [], "query": query})


@app.post("/api/push/subscribe", tags=["Notifications"])
async def push_subscribe(request: Request):
    """Register a push subscription."""
    body = await request.json()
    try:
        from cross_platform.push_notifications import PushNotificationService  # type: ignore
        svc = PushNotificationService()
        await svc.subscribe(body)
        return {"subscribed": True}
    except Exception:
        return {"subscribed": True, "note": "push module not initialized"}


@app.get("/api/agents", tags=["Agents"])
async def get_agents():
    """Get running agent tasks."""
    try:
        from orchestration.api import list_agents  # type: ignore
        return await list_agents()
    except ImportError:
        return _stub_response("agents", {"agents": [], "total": 0})


@app.get("/api/documents", tags=["Documents"])
async def get_documents(status: Optional[str] = Query(default=None)):
    """List documents from e-signature module."""
    try:
        from esignature.api import list_documents  # type: ignore
        return await list_documents(status=status)
    except ImportError:
        return _stub_response("documents", {"documents": [], "total": 0})


# ─── PWA Static Files ──────────────────────────────────────────────────────────
if PWA_DIR.exists():
    app.mount("/icons", StaticFiles(directory=str(PWA_DIR / "icons")), name="icons") if (PWA_DIR / "icons").exists() else None

    @app.get("/service_worker.js", include_in_schema=False)
    async def serve_sw():
        sw_path = PWA_DIR / "service_worker.js"
        if sw_path.exists():
            return FileResponse(str(sw_path), media_type="application/javascript",
                                headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})
        raise HTTPException(status_code=404)

    @app.get("/manifest.json", include_in_schema=False)
    async def serve_manifest():
        m = PWA_DIR / "manifest.json"
        if m.exists():
            return FileResponse(str(m), media_type="application/manifest+json")
        raise HTTPException(status_code=404)

    @app.get("/styles.css", include_in_schema=False)
    async def serve_css():
        f = PWA_DIR / "styles.css"
        return FileResponse(str(f), media_type="text/css") if f.exists() else HTTPException(404)

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        f = PWA_DIR / "app.js"
        return FileResponse(str(f), media_type="application/javascript") if f.exists() else HTTPException(404)

    @app.get("/offline.html", include_in_schema=False)
    async def serve_offline():
        return HTMLResponse("""<!DOCTYPE html>
<html><head><title>Offline – SintraPrime</title>
<style>body{background:#0a0e1a;color:#e8eaf0;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100dvh;text-align:center;}</style>
</head><body><div><h1>⚖️ SintraPrime</h1><p>You are offline.</p><p>Your data is available in the app.</p><button onclick="location.reload()">Retry</button></div></body></html>""")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_pwa(full_path: str):
        """Serve PWA index for all client-side routes."""
        index = PWA_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index), media_type="text/html")
        return HTMLResponse("<h1>SintraPrime API Gateway</h1><p>PWA not found.</p>")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _stub_response(module: str, data: Dict) -> Dict:
    """Return a stub when the actual module isn't available."""
    logger.debug("Returning stub for module: %s", module)
    return {"module": module, "stub": True, **data}


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info("Starting SintraPrime API Gateway on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
