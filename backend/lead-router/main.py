"""
SintraPrime Lead Router - Main FastAPI Application.

This is the backend service that:
1. Receives lead submissions from the intake form
2. Routes leads to the best specialist agent
3. Triggers automated emails and callback scheduling
4. Logs leads in Airtable CRM
5. Alerts assigned agents to review cases
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import config
from api.routes import router as leads_router

# Configure logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
    debug=config.DEBUG,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SintraPrime Lead Router",
        "version": config.API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/docs-info")
async def docs_info():
    """Documentation information."""
    return {
        "title": config.API_TITLE,
        "version": config.API_VERSION,
        "endpoints": {
            "POST /api/leads": "Submit a new lead intake form",
            "GET /api/leads/{lead_id}": "Get status of a submitted lead",
            "GET /api/agents": "List available agents",
            "GET /api/health": "Health check",
        },
    }


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle generic exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
        },
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("Starting SintraPrime Lead Router")
    logger.info(f"Debug mode: {config.DEBUG}")
    logger.info(f"Email provider: {config.EMAIL_PROVIDER}")
    logger.info(f"Tasklet integration: {'enabled' if config.TASKLET_API_ENABLED else 'disabled'}")
    logger.info(f"Slack integration: {'enabled' if config.SLACK_ENABLED else 'disabled'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down SintraPrime Lead Router")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=config.LOG_LEVEL.lower(),
    )
