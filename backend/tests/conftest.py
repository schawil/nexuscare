"""
conftest.py — Configuration globale pytest + fixtures partagées.
Gère la base de données SQLite en mémoire pour les tests.
"""
import warnings
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Importer TOUS les modèles AVANT de créer les tables
from nexuscare.core.database import Base, get_db
from nexuscare.main import app as main_app
import nexuscare.models  # noqa: F401

# Filtre les DeprecationWarnings
def pytest_configure(config):
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="httpx")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="jose")


# Création d'une DB temporaire par session de test
@pytest.fixture(scope="session")
def db_engine():
    """Crée un moteur SQLite avec fichier temporaire."""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_")
    os.close(fd)
    
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )
    
    # Crée toutes les tables
    Base.metadata.create_all(engine)
    
    yield engine
    
    # Nettoie
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """Crée la factory de sessions."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@pytest.fixture(autouse=True)
def reset_db(db_session_factory):
    """Vide la DB avant chaque test pour isolation totale."""
    Session = db_session_factory
    db = Session()
    try:
        # Supprime tout dans l'ordre des dépendances
        from nexuscare.models.parent import Parent
        from nexuscare.models.child import Child
        from nexuscare.models.refresh_token import RefreshToken
        from nexuscare.models.rule import Rule
        from nexuscare.models.app_usage import AppUsage
        from nexuscare.models.alert import Alert
        from nexuscare.models.permission_request import PermissionRequest
        
        for model in [PermissionRequest, AppUsage, Alert, Rule, RefreshToken, Child, Parent]:
            db.query(model).delete()
        db.commit()
    finally:
        db.close()
    yield


# Override de la dépendance get_db
@pytest.fixture(autouse=True)
def override_db(db_session_factory):
    """Override get_db pour tous les tests."""
    def _get_db():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()
    
    main_app.dependency_overrides[get_db] = _get_db
    yield
    main_app.dependency_overrides.clear()


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


@pytest.fixture
def db_session(db_session_factory):
    """
    Fixture pour obtenir une session DB directe dans les tests.
    Utilise la factory de sessions de test.
    """
    db = db_session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def child_token_headers(client: TestClient, auth_headers: dict) -> dict:
    """
    Fixture qui crée un enfant lié et retourne un token device pour l'enfant.
    Utilisé pour tester les endpoints appelés par l'APK Enfant.
    """
    # Crée un enfant (utilise 'name' pas 'first_name')
    resp_child = client.post(
        "/api/v1/children",
        json={"name": "Test Child", "age": 10},
        headers=auth_headers
    )
    assert resp_child.status_code == 201, f"Failed to create child: {resp_child.json()}"
    child_data = resp_child.json()
    child_id = child_data["id"]
    
    # Génère un code de liaison
    resp_code = client.post(
        f"/api/v1/children/{child_id}/link-code",
        headers=auth_headers
    )
    assert resp_code.status_code == 200, f"Failed to generate link code: {resp_code.json()}"
    code = resp_code.json()["code"]
    
    # Lie l'appareil avec un device_id Android fictif (nécessite le code)
    device_id = "android-test-device-xyz"
    resp_link = client.post(
        f"/api/v1/children/{child_id}/link-device",
        json={"code": code, "device_id": device_id},
        headers=auth_headers
    )
    assert resp_link.status_code == 200, f"Failed to link device: {resp_link.json()}"
    
    # Login device pour obtenir le token
    resp_login = client.post(
        "/api/v1/auth/device-login",
        json={"device_id": device_id}
    )
    assert resp_login.status_code == 200, f"Failed device login: {resp_login.json()}"
    
    return {"Authorization": f"Bearer {resp_login.json()['access_token']}"}