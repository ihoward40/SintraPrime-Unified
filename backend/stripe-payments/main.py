"""
Main FastAPI application for Stripe payments module
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as payment_router
from webhooks.webhook_handler import router as webhook_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SintraPrime Payments API",
    description="Payment processing and subscription management using Stripe",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(payment_router, tags=["payments"])
app.include_router(webhook_router, tags=["webhooks"])

# Health check
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "stripe-payments",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """API root endpoint"""
    return {
        "service": "SintraPrime Payments API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "endpoints": {
            "payments": "/api/docs",
            "webhooks": "/webhooks/stripe"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Run on startup"""
    logger.info("SintraPrime Payments API starting up...")
    logger.info("Payment processing enabled")
    logger.info("Webhook handler ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown"""
    logger.info("SintraPrime Payments API shutting down...")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
