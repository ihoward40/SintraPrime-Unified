import datetime
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def get_dashboard():
    """Admin dashboard data"""
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).date()
    return {"dashboard": "ok", "timestamp": str(timestamp)}
