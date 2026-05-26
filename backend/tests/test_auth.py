"""
Tests d'intégration — Module Auth
Utilise une base SQLite in-memory pour l'isolation complète.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from nexuscare.core.database import Base, get_db
from nexuscare.main import app

# ─── Base de données in-memory pour les tests ────────────────────────────────
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override le dependency AVANT la création du client de test
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="function")
def setup_db():
    """Recrée les tables avant chaque test et les supprime après."""
    # Crée toutes les tables dans la DB de test
    Base.metadata.create_all(bind=engine_test)
    yield
    # Nettoie après le test
    Base.metadata.drop_all(bind=engine_test)


# Créer les tables une fois au chargement du module pour les fixtures qui en ont besoin
Base.metadata.create_all(bind=engine_test)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def registered_parent(client: TestClient) -> dict:
    """Crée un parent et retourne la réponse complète (parent + tokens)."""
    response = client.post("/api/v1/auth/register", json={
        "full_name": "Sandrine Dupont",
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    assert response.status_code == 201
    return response.json()


# ─── Tests Register ───────────────────────────────────────────────────────────

class TestRegister:
    def test_register_success(self, client: TestClient):
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Sandrine Dupont",
            "email": "sandrine@test.com",
            "password": "motdepasse123",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["parent"]["email"] == "sandrine@test.com"
        assert body["parent"]["full_name"] == "Sandrine Dupont"
        assert "access_token" in body["tokens"]
        assert "refresh_token" in body["tokens"]
        assert body["tokens"]["token_type"] == "bearer"

    def test_register_duplicate_email(self, client: TestClient, registered_parent: dict):
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Autre Personne",
            "email": "sandrine@test.com",  # même email
            "password": "autrepass123",
        })
        assert resp.status_code == 409
        assert "existe déjà" in resp.json()["detail"]

    def test_register_password_too_short(self, client: TestClient):
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "test@test.com",
            "password": "abc1",  # trop court (< 8)
        })
        assert resp.status_code == 422

    def test_register_password_no_digit(self, client: TestClient):
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "test@test.com",
            "password": "motdepassesansChiffre",
        })
        assert resp.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        resp = client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": "pasunemail",
            "password": "motdepasse123",
        })
        assert resp.status_code == 422


# ─── Tests Login ──────────────────────────────────────────────────────────────

class TestLogin:
    def test_login_success(self, client: TestClient, registered_parent: dict):
        resp = client.post("/api/v1/auth/login", json={
            "email": "sandrine@test.com",
            "password": "motdepasse123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    def test_login_wrong_password(self, client: TestClient, registered_parent: dict):
        resp = client.post("/api/v1/auth/login", json={
            "email": "sandrine@test.com",
            "password": "mauvaismdp123",
        })
        assert resp.status_code == 401
        # Message générique — ne révèle pas si c'est l'email ou le mdp
        assert "incorrect" in resp.json()["detail"]

    def test_login_unknown_email(self, client: TestClient):
        resp = client.post("/api/v1/auth/login", json={
            "email": "inconnu@test.com",
            "password": "motdepasse123",
        })
        assert resp.status_code == 401


# ─── Tests Refresh ────────────────────────────────────────────────────────────

class TestRefresh:
    def test_refresh_success(self, client: TestClient, registered_parent: dict):
        refresh_token = registered_parent["tokens"]["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        # Rotation : nouveau refresh token différent
        assert body["refresh_token"] != refresh_token

    def test_refresh_token_rotation(self, client: TestClient, registered_parent: dict):
        """L'ancien refresh token ne doit plus fonctionner après rotation."""
        old_refresh = registered_parent["tokens"]["refresh_token"]
        client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        # Réutilisation de l'ancien token
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert resp.status_code == 401

    def test_refresh_invalid_token(self, client: TestClient):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "tokenbidon"})
        assert resp.status_code == 401


# ─── Tests Logout ─────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_success(self, client: TestClient, registered_parent: dict):
        refresh_token = registered_parent["tokens"]["refresh_token"]
        resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert resp.json()["message"] == "Déconnexion réussie."

    def test_logout_idempotent(self, client: TestClient, registered_parent: dict):
        """Double logout ne doit pas provoquer d'erreur."""
        refresh_token = registered_parent["tokens"]["refresh_token"]
        client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        assert resp.status_code == 200

    def test_token_unusable_after_logout(self, client: TestClient, registered_parent: dict):
        """Après logout, le refresh token ne doit plus permettre de refresh."""
        refresh_token = registered_parent["tokens"]["refresh_token"]
        client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401


# ─── Tests /me ────────────────────────────────────────────────────────────────

class TestMe:
    def test_me_authenticated(self, client: TestClient, registered_parent: dict):
        access_token = registered_parent["tokens"]["access_token"]
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "sandrine@test.com"

    def test_me_no_token(self, client: TestClient):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 403

    def test_me_invalid_token(self, client: TestClient):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer tokenbidon"}
        )
        assert resp.status_code == 401