"""
NexusCare Backend — Point d'entrée FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexuscare.core.config import settings
from nexuscare.core.database import engine, Base

# Import des routers (à décommenter au fur et à mesure)
# from nexuscare.routers import auth, children, rules, usage, alerts, requests

def create_application() -> FastAPI:
    """Factory pattern — facilite les tests d'intégration."""
    application = FastAPI(
        title="NexusCare API",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url=None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restreindre en prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Crée les tables au démarrage (remplacé par Alembic en prod)
    Base.metadata.create_all(bind=engine)

    @application.get("/health", tags=["system"])
    def health_check():
        """Endpoint de healthcheck — vérifie que le backend répond."""
        return {"status": "ok", "version": "1.0.0"}

    return application


app = create_application()
