"""
FastAPI application entrypoint.

Phase 0 scope only: app wiring, configuration, and a health check.
No business routes, auth, or database tables are added here.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.clients import router as clients_router
from app.api.dashboard import router as dashboard_router
from app.api.forms import router as forms_router
from app.api.health import router as health_router
from app.api.onboarding import router as onboarding_router
from app.api.portal import router as portal_router
from app.api.templates import router as templates_router
from app.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# Allows the Next.js frontend (Step 0.3) to call this API during local
# development. Origins are configurable via CORS_ORIGINS, not hardcoded.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(clients_router)
app.include_router(forms_router)
app.include_router(templates_router)
app.include_router(onboarding_router)
app.include_router(portal_router)
app.include_router(dashboard_router)
