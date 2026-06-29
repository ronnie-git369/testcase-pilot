"""TestCasePilot FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api import retrieval_router
from app.api import router as api_router

app = FastAPI(
    title="TestCasePilot API",
    description="An Agentic AI QA assistant that generates enterprise-quality "
    "test cases from software requirements.",
    version="0.1.0",
)

# Mount feature routes (e.g. /requirements/parse). main.py stays the thin
# composition root: it wires routers together but contains no route logic.
app.include_router(api_router)
app.include_router(retrieval_router)


@app.get("/")
def read_root():
    """Service banner."""
    return {"service": "TestCasePilot API", "status": "ok", "version": "0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
