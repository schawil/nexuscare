"""
NexusCare Backend — Point d'entrée FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from nexuscare.core.config import settings
from nexuscare.core.database import engine, Base
import nexuscare.models  # noqa: F401 — importe tous les modèles pour SQLAlchemy
from nexuscare.routers import auth as auth_router
from nexuscare.routers import children as children_router
from nexuscare.routers import rules as rules_router


def create_application() -> FastAPI:
    application = FastAPI(
        title="NexusCare API",
        version="1.0.0",
        description="Backend de contrôle parental NexusCare — Projet Master 1",
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
    Base.metadata.create_all(bind=engine)
    application.include_router(auth_router.router,     prefix="/api/v1")
    application.include_router(children_router.router, prefix="/api/v1")
    application.include_router(rules_router.router,    prefix="/api/v1")

    @application.get("/health", tags=["Système"])
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return application


app = create_application()
