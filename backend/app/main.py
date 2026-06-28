"""TestCasePilot FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="TestCasePilot API",
    description="An Agentic AI QA assistant that generates enterprise-quality "
    "test cases from software requirements.",
    version="0.1.0",
)


@app.get("/")
def read_root():
    """Service banner."""
    return {"service": "TestCasePilot API", "status": "ok", "version": "0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}
