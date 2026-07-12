from fastapi import FastAPI
from backend.stripe_payments.api.routes import router as monetization_router

app = FastAPI()

app.include_router(monetization_router)

@app.get("/")
def root():
    return {"status": "SintraPrime API running"}