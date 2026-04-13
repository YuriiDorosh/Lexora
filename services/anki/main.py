"""
Anki Import Service — M0 stub.

Parses .apkg and .txt (tab-separated) Anki exports, normalises entries,
deduplicates against existing user data, and returns import results.
Real implementation begins in M5.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Lexora Anki Import Service",
    description="Anki deck import service (.apkg, .txt). M0 stub.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "anki"}
