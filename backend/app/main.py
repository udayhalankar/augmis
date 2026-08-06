from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import escalations
from app.api.routes import conversations
from app.api.routes import auth
from app.api.routes import audit
from app.api.routes import subscriptions
from app.api.routes import platform
from app.api.routes import agents
from app.api.routes import repositories
from app.api.routes import repository_sync
from app.api.routes import scope_tracker
from app.api.routes import symployees
from app.api.routes import symployee_record_configuration
from app.services.connector_scheduler_service import (
    start_connector_scheduler,
    stop_connector_scheduler,
)

from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.search import router as search_router
from app.api.routes.ai import router as ai_router
from app.api.routes.dashboard import router as dashboard_router
from app.core.config import settings
from app.core.logging import configure_application_logging
from app.core.request_middleware import request_context_middleware
# from init_db import init_db

configure_application_logging()

app = FastAPI(
    title="Infomentica DSS Enterprise API",
    version="1.2B",
    description="FastAPI backend for AI-powered Decision Support System"
)

app.middleware("http")(request_context_middleware)


# @app.on_event("startup")
# def ensure_database_schema():
#     init_db()


@app.on_event("startup")
def start_background_connector_scheduler():
    start_connector_scheduler()


@app.on_event("shutdown")
def stop_background_connector_scheduler():
    stop_connector_scheduler()

app.include_router(escalations.router)
app.include_router(conversations.router)
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(subscriptions.router)
app.include_router(platform.router)
app.include_router(agents.router)
app.include_router(repository_sync.router)
app.include_router(repositories.router)
app.include_router(scope_tracker.router)
app.include_router(symployees.router)
app.include_router(symployee_record_configuration.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ALLOW_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(ingestion_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
