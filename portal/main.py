import datetime
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    """Health check endpoint"""
    timestamp = datetime.datetime.now(tz=datetime.timezone.utc).date()
    return {"status": "healthy", "timestamp": str(timestamp)}
