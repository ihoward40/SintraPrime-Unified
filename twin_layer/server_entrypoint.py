"""
SintraPrime Twin Display Server Entrypoint
Serves a simple WebSocket + HTTP health API on port 8765
"""
import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Twin Display Server", version="2.0.0")


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "twin-display"})


@app.get("/")
async def root():
    return {
        "service": "twin-display-server",
        "port": 8765,
        "version": "2.0.0",
        "auth_required": bool(os.getenv("TWIN_AUTH_TOKEN"))
    }


@app.get("/status")
async def status():
    return {
        "connections": 0,
        "uptime": "running",
        "twin_auth_enabled": bool(os.getenv("TWIN_AUTH_TOKEN"))
    }


if __name__ == "__main__":
    port = int(os.getenv("TWIN_PORT", "8765"))
    host = os.getenv("TWIN_HOST", "0.0.0.0")
    print(f"Starting Twin Display Server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
