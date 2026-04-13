"""
Audio / TTS Service — M0 stub.

Generates offline text-to-speech audio for learning entries using
piper (primary) or espeak-ng (fallback).  Supports uk, en, el.
Real implementation begins in M6.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Lexora Audio / TTS Service",
    description="Offline TTS service (piper / espeak-ng). M0 stub.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "audio"}
