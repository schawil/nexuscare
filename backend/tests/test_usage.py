"""
Tests unitaires — Module Usage
Couvre l'envoi de rapports d'utilisation et la récupération des données.
"""
import pytest
from datetime import date, timedelta
from fastapi import status
from httpx import Client

from nexuscare.core.security import create_device_token


class TestReportUsage:
    """Tests pour POST /api/v1/children/{child_id}/usage"""

    def test_report_usage_success(self, client: Client, auth_headers: dict, child_id: int):
        """Un enfant peut envoyer un rapport d'utilisation."""
        # D'abord, on lie un device_id à l'enfant
        device_id = "android-test-device-001"
        resp = client.post(
            f"/api/v1/children/{child_id}/link-device",
            json={"device_id": device_id},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK

        # Crée un token device
        from nexuscare.models.child import Child
        from nexuscare.core.database import SessionLocal
        db = SessionLocal()
        child = db.get(Child, child_id)
        token = create_device_token(child.id, device_id)
        db.close()

        device_headers = {"Authorization": f"Bearer {token}"}

        # Envoie un rapport d'utilisation
        payload = {
            "usages": [
                {
                    "package_name": "com.tiktok.android",
                    "app_name": "TikTok",
                    "duration_seconds": 300,
                    "usage_date": str(date.today()),
                },
                {
                    "package_name": "com.instagram.android",
                    "app_name": "Instagram",
                    "duration_seconds": 600,
                    "usage_date": str(date.today()),
                },
            ]
        }

        resp = client.post(
            f"/api/v1/children/{child_id}/usage",
            json=payload,
            headers=device_headers,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert "entrées enregistrées" in data["message"]

    def test_report_usage_upsert_adds_duration(self, client: Client, auth_headers: dict, child_id: int):
        """UPSERT : si une entrée existe, la durée est additionnée."""
        device_id = "android-test-device-002"
        client.post(
            f"/api/v1/children/{child_id}/link-device",
            json={"device_id": device_id},
            headers=auth_headers,
        )

        from nexuscare.models.child import Child
        from nexuscare.core.database import SessionLocal
        db = SessionLocal()
        child = db.get(Child, child_id)
        token = create_device_token(child.id, device_id)
        db.close()

        device_headers = {"Authorization": f"Bearer {token}"}
        today = str(date.today())

        # Premier rapport
        payload1 = {
            "usages": [{
                "package_name": "com.youtube.android",
                "app_name": "YouTube",
                "duration_seconds": 100,
                "usage_date": today,
            }]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload1, headers=device_headers)

        # Deuxième rapport pour la même app
        payload2 = {
            "usages": [{
                "package_name": "com.youtube.android",
                "app_name": "YouTube",
                "duration_seconds": 50,
                "usage_date": today,
            }]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload2, headers=device_headers)

        # Vérifie que la durée totale est 150
        resp = client.get(
            f"/api/v1/children/{child_id}/usage/today",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        youtube_entry = next((e for e in data["entries"] if e["package_name"] == "com.youtube.android"), None)
        assert youtube_entry is not None
        assert youtube_entry["total_seconds"] == 150

    def test_report_usage_wrong_child_token(self, client: Client, auth_headers: dict, child_id: int):
        """Un token enfant ne peut pas envoyer pour un autre enfant."""
        # Crée un premier enfant et lie un device
        device_id = "android-test-device-003"
        client.post(
            f"/api/v1/children/{child_id}/link-device",
            json={"device_id": device_id},
            headers=auth_headers,
        )

        # Crée un deuxième enfant
        resp = client.post(
            "/api/v1/children",
            json={"name": "Deuxième Enfant", "age": 10},
            headers=auth_headers,
        )
        other_child_id = resp.json()["id"]

        from nexuscare.models.child import Child
        from nexuscare.core.database import SessionLocal
        db = SessionLocal()
        child = db.get(Child, child_id)
        token = create_device_token(child.id, device_id)
        db.close()

        device_headers = {"Authorization": f"Bearer {token}"}

        # Tente d'envoyer pour l'autre enfant → 403
        payload = {
            "usages": [{
                "package_name": "com.test.app",
                "app_name": "Test",
                "duration_seconds": 100,
                "usage_date": str(date.today()),
            }]
        }
        resp = client.post(
            f"/api/v1/children/{other_child_id}/usage",
            json=payload,
            headers=device_headers,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


class TestGetTodayUsage:
    """Tests pour GET /api/v1/children/{child_id}/usage/today"""

    def test_get_today_empty(self, client: Client, auth_headers: dict, child_id: int):
        """Récupère l'usage du jour vide si aucune donnée."""
        resp = client.get(
            f"/api/v1/children/{child_id}/usage/today",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["date"] == str(date.today())
        assert data["total_seconds"] == 0
        assert data["entries"] == []

    def test_get_today_with_data(self, client: Client, auth_headers: dict, child_id: int):
        """Récupère l'usage du jour avec des données."""
        # Lie un device et envoie des données
        device_id = "android-test-device-004"
        client.post(
            f"/api/v1/children/{child_id}/link-device",
            json={"device_id": device_id},
            headers=auth_headers,
        )

        from nexuscare.models.child import Child
        from nexuscare.core.database import SessionLocal
        db = SessionLocal()
        child = db.get(Child, child_id)
        token = create_device_token(child.id, device_id)
        db.close()

        device_headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "usages": [{
                "package_name": "com.netflix.mediaclient",
                "app_name": "Netflix",
                "duration_seconds": 1800,
                "usage_date": str(date.today()),
            }]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload, headers=device_headers)

        resp = client.get(
            f"/api/v1/children/{child_id}/usage/today",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["total_seconds"] == 1800
        assert len(data["entries"]) == 1
        assert data["entries"][0]["package_name"] == "com.netflix.mediaclient"

    def test_get_today_isolation(self, client: Client, auth_headers: dict, child_id: int):
        """Un parent ne peut pas voir l'usage d'un autre parent."""
        # Crée un deuxième parent et enfant
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Autre Parent",
                "email": "autre@example.com",
                "password": "motdepasse123",
            },
        )
        other_tokens = resp.json()["tokens"]
        other_headers = {"Authorization": f"Bearer {other_tokens['access_token']}"}

        resp = client.post(
            "/api/v1/children",
            json={"name": "Autre Enfant", "age": 8},
            headers=other_headers,
        )
        other_child_id = resp.json()["id"]

        # Tente d'accéder à l'usage de l'autre enfant → 404
        resp = client.get(
            f"/api/v1/children/{other_child_id}/usage/today",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestGetWeeklyUsage:
    """Tests pour GET /api/v1/children/{child_id}/usage/weekly"""

    def test_get_weekly_returns_7_days(self, client: Client, auth_headers: dict, child_id: int):
        """Retourne toujours 7 jours, même vides."""
        resp = client.get(
            f"/api/v1/children/{child_id}/usage/weekly",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["days"]) == 7
        # Vérifie que les dates sont consécutives
        for i in range(len(data["days"]) - 1):
            d1 = date.fromisoformat(data["days"][i]["date"])
            d2 = date.fromisoformat(data["days"][i + 1]["date"])
            assert (d2 - d1).days == 1

    def test_get_weekly_with_data(self, client: Client, auth_headers: dict, child_id: int):
        """Retourne les données des 7 derniers jours."""
        device_id = "android-test-device-005"
        client.post(
            f"/api/v1/children/{child_id}/link-device",
            json={"device_id": device_id},
            headers=auth_headers,
        )

        from nexuscare.models.child import Child
        from nexuscare.core.database import SessionLocal
        db = SessionLocal()
        child = db.get(Child, child_id)
        token = create_device_token(child.id, device_id)
        db.close()

        device_headers = {"Authorization": f"Bearer {token}"}

        # Envoie des données pour aujourd'hui et hier
        today = date.today()
        yesterday = today - timedelta(days=1)

        payload = {
            "usages": [
                {
                    "package_name": "com.test.app",
                    "app_name": "Test",
                    "duration_seconds": 100,
                    "usage_date": str(today),
                },
                {
                    "package_name": "com.test.app",
                    "app_name": "Test",
                    "duration_seconds": 200,
                    "usage_date": str(yesterday),
                },
            ]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload, headers=device_headers)

        resp = client.get(
            f"/api/v1/children/{child_id}/usage/weekly",
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        
        today_entry = next((d for d in data["days"] if d["date"] == str(today)), None)
        yesterday_entry = next((d for d in data["days"] if d["date"] == str(yesterday)), None)
        
        assert today_entry is not None
        assert today_entry["total_seconds"] == 100
        assert yesterday_entry is not None
        assert yesterday_entry["total_seconds"] == 200


class TestGetDailyUsage:
    """Tests pour GET /api/v1/children/{child_id}/usage/daily?date=YYYY-MM-DD"""

    def test_get_daily_specific_date(self, client: Client, auth_headers: dict, child_id: int):
        """Récupère l'usage d'un jour précis."""
        target_date = date.today() - timedelta(days=3)
        
        resp = client.get(
            f"/api/v1/children/{child_id}/usage/daily",
            params={"date": str(target_date)},
            headers=auth_headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["date"] == str(target_date)
        assert data["total_seconds"] == 0
