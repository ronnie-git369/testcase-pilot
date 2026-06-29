"""HTTP API layer for TestCasePilot.

Exposes the router that aggregates the application's routes. Kept separate from
services and models so the web framework stays at the outer edge of the system.
"""

from app.api.retrieval_routes import router as retrieval_router
from app.api.routes import router

__all__ = ["router", "retrieval_router"]
