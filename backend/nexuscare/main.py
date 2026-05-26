"""
NexusCare Backend — Point d'entrée FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexuscare.core.config import settings
from nexuscare.core.database import Base

# Import de tous les modèles pour que SQLAlchemy crée les tables
import nexuscare.models  # noqa: F401

from nexuscare.routers import auth as auth_router


def create_application() -> FastAPI:
    application = FastAPI(
        title="NexusCare API",
        version="1.0.0",
        description="Backend de contrôle parental NexusCare",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────────────────
    application.include_router(auth_router.router, prefix="/api/v1")

    @application.get("/health", tags=["Système"])
    def health_check():
        """Endpoint de healthcheck — vérifie que le backend répond."""
        return {"status": "ok", "version": "1.0.0"}

    return application


app = create_application()