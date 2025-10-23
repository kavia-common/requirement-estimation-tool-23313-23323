from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import select, func

from src.db.session import init_db, get_session
from src.db.models import touch_models_metadata, RequirementCatalog, Settings
from src.db.migrations.bootstrap import run_bootstrap
from src.api.routers.requirements import router as requirements_router
from src.api.routers.estimates import router as estimates_router

app = FastAPI(
    title="Estimate Backend API",
    description="Backend API for processing user estimate requests and data access logic.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Service health and diagnostics"},
        {"name": "requirements", "description": "Requirement catalog APIs (CRUD, search, pagination)"},
        {"name": "estimates", "description": "Estimates and items APIs (CRUD, totals)"},
        {"name": "database", "description": "Database and persistence operations"},
    ],
)

# CORS configuration
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

    Steps:
    1) Ensure models are imported so metadata is populated.
    2) Create tables if they do not exist yet (dev/local).
    3) Run bootstrap seeding if tables are empty.
    """
    # 1) Ensure models are loaded
    touch_models_metadata()

    # 2) Create all tables
    await init_db()

    # 3) Seed data if needed
    async with get_session() as session:
        # If both settings and catalog have no rows, assume first-time init
        settings_count = (await session.execute(select(func.count(Settings.id)))).scalar_one() or 0
        catalog_count = (await session.execute(select(func.count(RequirementCatalog.id)))).scalar_one() or 0
        if settings_count == 0 or catalog_count == 0:
            await run_bootstrap(session)


# Register routers
app.include_router(requirements_router)
app.include_router(estimates_router)


# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Health check endpoint to verify the service is running.

    Returns:
        JSON object with a 'message' field confirming service availability.
    """
    return {"message": "Healthy"}
