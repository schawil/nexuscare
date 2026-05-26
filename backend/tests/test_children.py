"""
Tests d'intégration — Module Children (37 tests au total avec Auth)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nexuscare.core.database import Base, get_db
from nexuscare.main import app

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    client.post("/api/v1/auth/register", json={
        "full_name": "Sandrine Dupont",
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "sandrine@test.com",
        "password": "motdepasse123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def created_child(client: TestClient, auth_headers: dict) -> dict:
    resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateChild:
    def test_create_childhood(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Léo"
        assert body["profile_tier"] == "CHILDHOOD"
        assert body["is_linked"] is False

    def test_create_preadolescence(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Emma", "age": 13}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_age_boundary_min(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Mini", "age": 6}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "CHILDHOOD"

    def test_age_boundary_max(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Ado", "age": 15}, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_age_too_young(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Bébé", "age": 5}, headers=auth_headers)
        assert resp.status_code == 422

    def test_age_too_old(self, client, auth_headers):
        resp = client.post("/api/v1/children", json={"name": "Adulte", "age": 16}, headers=auth_headers)
        assert resp.status_code == 422

    def test_requires_auth(self, client):
        resp = client.post("/api/v1/children", json={"name": "Léo", "age": 8})
        assert resp.status_code == 403


class TestListChildren:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/api/v1/children", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_multiple(self, client, auth_headers):
        client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        client.post("/api/v1/children", json={"name": "Emma", "age": 13}, headers=auth_headers)
        resp = client.get("/api/v1/children", headers=auth_headers)
        assert len(resp.json()) == 2

    def test_isolation_between_parents(self, client, auth_headers):
        client.post("/api/v1/children", json={"name": "Léo", "age": 8}, headers=auth_headers)
        client.post("/api/v1/auth/register", json={
            "full_name": "Autre", "email": "autre@test.com", "password": "motdepasse123"
        })
        r = client.post("/api/v1/auth/login", json={"email": "autre@test.com", "password": "motdepasse123"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert client.get("/api/v1/children", headers=h2).json() == []


class TestGetChild:
    def test_get_existing(self, client, auth_headers, created_child):
        resp = client.get(f"/api/v1/children/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200

    def test_get_not_found(self, client, auth_headers):
        assert client.get("/api/v1/children/9999", headers=auth_headers).status_code == 404

    def test_cannot_access_other_parent_child(self, client, auth_headers, created_child):
        client.post("/api/v1/auth/register", json={
            "full_name": "Autre", "email": "autre@test.com", "password": "motdepasse123"
        })
        r = client.post("/api/v1/auth/login", json={"email": "autre@test.com", "password": "motdepasse123"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
        assert client.get(f"/api/v1/children/{created_child['id']}", headers=h2).status_code == 404


class TestUpdateChild:
    def test_update_name(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"name": "Léo Updated"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Léo Updated"

    def test_update_age_changes_tier(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"age": 12}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["profile_tier"] == "PREADOLESCENCE"

    def test_partial_update(self, client, auth_headers, created_child):
        resp = client.patch(f"/api/v1/children/{created_child['id']}",
                            json={"name": "Léo Nouveau"}, headers=auth_headers)
        assert resp.json()["age"] == created_child["age"]


class TestDeleteChild:
    def test_delete(self, client, auth_headers, created_child):
        resp = client.delete(f"/api/v1/children/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert client.get(f"/api/v1/children/{created_child['id']}", headers=auth_headers).status_code == 404

    def test_delete_not_found(self, client, auth_headers):
        assert client.delete("/api/v1/children/9999", headers=auth_headers).status_code == 404


class TestLinkDevice:
    def test_generate_code(self, client, auth_headers, created_child):
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-code", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["code"]) == 6 and body["code"].isdigit()
        assert body["expires_in"] == 600

    def test_link_success(self, client, auth_headers, created_child):
        code = client.post(f"/api/v1/children/{created_child['id']}/link-code",
                           headers=auth_headers).json()["code"]
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": code, "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_linked"] is True

    def test_wrong_code(self, client, auth_headers, created_child):
        client.post(f"/api/v1/children/{created_child['id']}/link-code", headers=auth_headers)
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": "000000", "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_no_code_generated(self, client, auth_headers, created_child):
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": "123456", "device_id": "android-001"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_code_single_use(self, client, auth_headers, created_child):
        code = client.post(f"/api/v1/children/{created_child['id']}/link-code",
                           headers=auth_headers).json()["code"]
        client.post(f"/api/v1/children/{created_child['id']}/link-device",
                    json={"code": code, "device_id": "android-001"}, headers=auth_headers)
        resp = client.post(f"/api/v1/children/{created_child['id']}/link-device",
                           json={"code": code, "device_id": "android-002"}, headers=auth_headers)
        assert resp.status_code == 400
