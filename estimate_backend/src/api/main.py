from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.session import init_db

app = FastAPI(
    title="Estimate Backend API",
    description="Backend API for processing user estimate requests and data access logic.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and diagnostics"},
        {"name": "database", "description": "Database and persistence operations"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # NOTE: tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize resources such as the database on app startup.

    For local/dev, this will create tables if they do not exist yet.
    In production, prefer migration workflows (Alembic).
    """
    await init_db()


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"message": "Healthy"}
