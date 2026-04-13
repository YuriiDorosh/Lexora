"""
LLM Enrichment Service — M0 stub.

Generates synonyms, antonyms, example sentences, and explanations
using a local model (Qwen3 8B or equivalent, ≤20 GB).
Real implementation begins in M4.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Lexora LLM Enrichment Service",
    description="Local LLM enrichment service (Qwen3 8B). M0 stub.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "llm"}
