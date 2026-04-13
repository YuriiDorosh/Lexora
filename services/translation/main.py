"""
Translation Service — M0 stub.

Provides offline translation between uk/en/el via Argos Translate.
Real implementation begins in M3.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Lexora Translation Service",
    description="Offline translation service (Argos Translate). M0 stub.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "translation"}
