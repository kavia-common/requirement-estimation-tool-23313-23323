from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db import engine
from src.db.models import Base

# Initialize FastAPI with basic metadata for OpenAPI/Swagger
app = FastAPI(
    title="Requirement Estimation Backend",
    description="Backend API for requirement estimation and related data access.",
    version="0.1.0",
)

# Enable permissive CORS (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure tables exist at startup (simple projects; migrations recommended for production)
@app.on_event("startup")
def on_startup():
    # Create tables if they don't exist.
    Base.metadata.create_all(bind=engine)

# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["Health"])
def health_check():
    """Simple health check endpoint.

    Returns:
        JSON payload with a message to indicate service health.
    """
    return {"message": "Healthy"}
