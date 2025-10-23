import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db import engine
from src.db.models import Base
from src.api.routers.requirements import router as requirements_router
from src.api.routers.estimates import router as estimates_router
from src.api.routers.reference import router as reference_router

# Initialize FastAPI with basic metadata for OpenAPI/Swagger
app = FastAPI(
    title="Requirement Estimation Backend",
    description="Backend API for requirement estimation and related data access.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health and diagnostics"},
        {"name": "Requirements", "description": "Manage requirements"},
        {"name": "Estimates", "description": "Manage estimates and items; calculate totals"},
        {"name": "Reference Data", "description": "Rate cards and complexity defaults"},
    ],
)

# Configure CORS from environment (comma-separated), fallback to '*'
cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins.split(",")] if cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure tables exist at startup (simple projects; migrations recommended for production)
@app.on_event("startup")
def on_startup():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["Health"])
def health_check():
    """Simple health check endpoint.

    Returns:
        JSON payload with a message to indicate service health.
    """
    return {"message": "Healthy"}

# Mount API routers under /api/v1
app.include_router(requirements_router, prefix="/api/v1")
app.include_router(estimates_router, prefix="/api/v1")
app.include_router(reference_router, prefix="/api/v1")


# PUBLIC_INTERFACE
@app.get(
    "/api/v1/websocket-usage",
    tags=["Health"],
    summary="WebSocket usage note",
)
def websocket_usage_note():
    """Provide project-level note for any prospective WebSocket usage.

    Returns:
        A simple note; this project currently does not expose WebSocket endpoints.
    """
    return {"note": "No WebSocket endpoints are defined in this service at present."}
