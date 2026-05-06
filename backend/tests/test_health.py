"""Test de smoke : vérifie que le serveur démarre et répond."""
from fastapi.testclient import TestClient
from nexuscare.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
