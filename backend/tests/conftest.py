"""
conftest.py — Configuration globale pytest + fixtures partagées.
Gère la base de données SQLite en mémoire pour les tests.

IMPORTANT: Pour SQLite en mémoire avec FastAPI TestClient (qui utilise des threads),
nous devons utiliser un fichier temporaire ou StaticMemoryPool pour partager la DB
entre le thread principal et le thread du TestClient.
"""
import warnings
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importer TOUS les modèles AVANT de créer les tables
# Cela garantit que SQLAlchemy connaît toutes les tables
from nexuscare.core.database import Base, get_db
from nexuscare.main import app as main_app
import nexuscare.models  # noqa: F401 — assure que tous les modèles sont chargés


# Filtre les DeprecationWarnings des dépendances tierces
def pytest_configure(config):
    """Filtre les warnings de libs tierces au démarrage de pytest."""
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="jose")


# Option 1: Utiliser StaticPool pour garder la DB en mémoire partagée entre threads
# C'est la solution recommandée pour les tests rapides
# Note: on utilise file::memory:?cache=shared avec StaticPool pour une compatibilité maximale
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared"
engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # IMPORTANT: permet le partage entre threads
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    """Override de la dépendance get_db pour utiliser la DB de test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Applique l'override AVANT que les tests ne commencent
main_app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """
    Fixture automatique qui crée/détruit le schéma DB avant/après chaque test.
    Utilise autouse=True pour s'exécuter automatiquement pour tous les tests.
    """
    # Crée TOUTES les tables connues par SQLAlchemy
    Base.metadata.create_all(bind=engine_test)
    yield
    # Nettoie après le test
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client() -> TestClient:
    """Client de test FastAPI."""
    return TestClient(main_app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    """
    Fixture qui enregistre un parent, se connecte et retourne les headers d'authentification.
    Réutilisable par tous les tests nécessitant une authentification.
    """
    # Register
    resp_reg = client.post("/api/v1/auth/register", json={
        "full_name": "Sandrine Dupont",
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    assert resp_reg.status_code == 201, f"Register failed: {resp_reg.json()}"
    
    # Login
    resp_login = client.post("/api/v1/auth/login", json={
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    assert resp_login.status_code == 200, f"Login failed: {resp_login.json()}"
    
    return {"Authorization": f"Bearer {resp_login.json()['access_token']}"}


@pytest.fixture
def created_child(client: TestClient, auth_headers: dict) -> dict:
    """
    Fixture qui crée un enfant de test avec profil CHILDHOOD.
    Réutilisable par les tests CRUD children.
    """
    resp = client.post(
        "/api/v1/children",
        json={"name": "Léo", "age": 8},
        headers=auth_headers
    )
    assert resp.status_code == 201, f"Create child failed: {resp.json()}"
    return resp.json()