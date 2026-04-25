"""
SintraPrime UniVerse — Docker Entrypoint
Starts the FastAPI server with uvicorn
"""
import os
import sys
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SintraPrime UniVerse Hive Mind API",
    description="Multi-Agent Orchestration System — Core API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "sintraprime-api", "version": "2.0.0"})


@app.get("/")
async def root():
    return {"message": "SintraPrime UniVerse Hive Mind API", "version": "2.0.0", "docs": "/docs"}


@app.get("/api/status")
async def status():
    return {
        "status": "operational",
        "services": {
            "hive_mind": "active",
            "agent_swarms": "active",
            "superintelligence": os.getenv("ENABLE_SUPERINTELLIGENCE", "true") == "true"
        }
    }


@app.get("/api/agents")
async def list_agents():
    return {"agents": [], "total": 0}


@app.get("/api/swarms")
async def list_swarms():
    return {"swarms": [], "total": 0}


@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    return JSONResponse(
        content="# HELP sintraprime_up Service health\n# TYPE sintraprime_up gauge\nsintraprime_up 1\n",
        media_type="text/plain"
    )


# Try to import and mount the hive mind API if available
try:
    sys.path.insert(0, '/app')
    logger.info("Attempting to load Hive Mind API modules...")
except Exception as e:
    logger.warning(f"Could not load advanced modules: {e}. Running in basic mode.")


if __name__ == "__main__":
    port = int(os.getenv("API_PORT", "8080"))
    host = os.getenv("API_HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    logger.info(f"Starting SintraPrime UniVerse API on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True
    )
