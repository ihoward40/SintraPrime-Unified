"""Admin Dashboard — Real-time metrics & WebSocket updates."""
import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from portal.core.settings import get_settings
from portal.middleware.auth import verify_token

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()

# In-memory metrics store
metrics_store = {
    "requests_total": 0,
    "requests_per_sec": 0.0,
    "avg_response_time_ms": 0.0,
    "error_rate": 0.0,
    "active_sessions": 0,
    "uptime_seconds": 0,
    "last_updated": datetime.now(UTC).isoformat(),
}

@router.get("/dashboard")
async def get_dashboard(token: str = Depends(verify_token)):
    """Serve dashboard HTML."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SintraPrime Admin Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .dashboard { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
            .metric { background: white; padding: 20px: border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
            .metric-label { font-size: 12px; color: #666; margin-top: 5px; }
            canvas { width: 100%; }
        </style>
    </head>
    <body>
        <h1>SintraPrime Admin Dashboard</h1>
        <div class="dashboard">
            <div class="metric">
                <div class="metric-value" id="requests">0</div>
                <div class="metric-label">Total Requests</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="rps">0.0</div>
                <div class="metric-label">Requests/sec</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="latency">0ms</div>
                <div class="metric-label">Avg Response Time</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="errors">0%</div>
                <div class="metric-label">Error Rate</div>
            </div>
        </div>
        <script>
            const ws = new WebSocket("ws://localhost:8000/admin/ws");
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                document.getElementById("requests").textContent = data.requests_total;
                document.getElementById("rps").textContent = data.requests_per_sec.toFixed(1);
                document.getElementById("latency").textContent = data.avg_response_time_ms.toFixed(0) + "ms";
                document.getElementById("errors").textContent = data.error_rate.toFixed(1) + "%";
            };
        </script>
    </body>
    </html>
    """)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Depends(verify_token)):
    """WebSocket endpoint for real-time metric streaming."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(metrics_store)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@router.get("/metrics")
async def get_metrics(token: str = Depends(verify_token)):
    """REST endpoint for metrics."""
    return metrics_store

@router.post("/metrics/update")
async def update_metrics(data: dict, token: str = Depends(verify_token)):
    """Update metrics store."""
    metrics_store.update(data)
    metrics_store["last_updated"] = datetime.now(UTC).isoformat()
    return {"status": "updated"}
