"""
Tests du module Usage — temps d'écran par application.
Couvre : report, today, weekly, daily, summary, cleanup
Objectif : 10+ tests passing
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from nexuscare.core.database import get_db
from nexuscare.models.app_usage import AppUsage
from nexuscare.models.child import Child
from nexuscare.models.rule import Rule


# Enum pour les types de règles (à synchroniser avec le modèle)
class RuleType:
    SCREEN_LIMIT = "SCREEN_LIMIT"
    APP_BLOCK = "APP_BLOCK"
    APP_TIME_LIMIT = "APP_TIME_LIMIT"
    TIME_SLOT = "TIME_SLOT"


class TestReportUsage:
    """Tests pour POST /children/{id}/usage — rapport envoyé par l'enfant."""

    def test_report_usage_success(self, client: TestClient, db_session: Session, child_token_headers: dict):
        """Un enfant peut rapporter son usage."""
        # Récupère l'enfant lié créé par la fixture child_token_headers
        from nexuscare.core.security import decode_access_token
        token = child_token_headers["Authorization"].split(" ")[1]
        payload = decode_access_token(token, return_payload=True)
        child_id = int(payload["sub"])
        
        payload = {
            "usages": [
                {
                    "package_name": "com.tiktok.android",
                    "app_name": "TikTok",
                    "duration_seconds": 1800,
                    "usage_date": str(datetime.now(timezone.utc).date()),
                },
                {
                    "package_name": "com.youtube.android",
                    "app_name": "YouTube",
                    "duration_seconds": 900,
                    "usage_date": str(datetime.now(timezone.utc).date()),
                },
            ]
        }
        
        resp = client.post(f"/api/v1/children/{child_id}/usage", json=payload, headers=child_token_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries_processed"] == 2
        assert data["entries_created"] == 2

    def test_report_usage_upsert_adds_duration(self, client: TestClient, db_session: Session, child_token_headers: dict):
        """Le rapport UPSERT additionne les durées pour une même app/date."""
        # Récupère l'enfant lié créé par la fixture
        from nexuscare.core.security import decode_access_token
        token = child_token_headers["Authorization"].split(" ")[1]
        payload = decode_access_token(token, return_payload=True)
        child_id = int(payload["sub"])
        
        today = str(datetime.now(timezone.utc).date())
        
        # Premier rapport
        payload1 = {
            "usages": [{
                "package_name": "com.instagram.android",
                "app_name": "Instagram",
                "duration_seconds": 600,
                "usage_date": today,
            }]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload1, headers=child_token_headers)
        
        # Deuxième rapport (même app, même jour)
        payload2 = {
            "usages": [{
                "package_name": "com.instagram.android",
                "app_name": "Instagram",
                "duration_seconds": 300,
                "usage_date": today,
            }]
        }
        client.post(f"/api/v1/children/{child_id}/usage", json=payload2, headers=child_token_headers)
        
        # Vérifie que la durée totale est 900 (600 + 300)
        usage = db_session.query(AppUsage).filter(
            AppUsage.child_id == child_id,
            AppUsage.package_name == "com.instagram.android",
        ).first()
        assert usage.duration_seconds == 900

    def test_report_usage_invalid_duration(self, client: TestClient, db_session, child_token_headers: dict):
        """Durée négative rejetée."""
        # Récupère l'enfant lié créé par la fixture
        from nexuscare.core.security import decode_access_token
        token = child_token_headers["Authorization"].split(" ")[1]
        payload = decode_access_token(token, return_payload=True)
        child_id = int(payload["sub"])
        
        payload = {
            "usages": [{
                "package_name": "com.test.app",
                "app_name": "Test",
                "duration_seconds": -100,
                "usage_date": str(datetime.now(timezone.utc).date()),
            }]
        }
        
        resp = client.post(f"/api/v1/children/{child_id}/usage", json=payload, headers=child_token_headers)
        assert resp.status_code == 422

    def test_report_usage_wrong_child(self, client: TestClient, db_session, child_token_headers: dict, auth_headers: dict):
        """Un enfant ne peut pas rapporter l'usage d'un autre enfant."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        
        # Crée un deuxième enfant
        child2 = Child(parent_id=parent.id, name="Child2", age=8, profile_tier="CHILDHOOD", device_id="android-c2")
        db_session.add(child2)
        db_session.commit()
        
        # Token de child1 essaie de poster pour child2
        payload = {
            "usages": [{
                "package_name": "com.test.app",
                "app_name": "Test",
                "duration_seconds": 100,
                "usage_date": str(datetime.now(timezone.utc).date()),
            }]
        }
        
        resp = client.post(f"/api/v1/children/{child2.id}/usage", json=payload, headers=child_token_headers)
        assert resp.status_code == 403


class TestGetTodayUsage:
    """Tests pour GET /children/{id}/usage/today."""

    def test_get_today_empty(self, client: TestClient, db_session, auth_headers: dict):
        """Aujourd'hui sans usage retourne total à 0."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_seconds"] == 0
        assert data["apps"] == []

    def test_get_today_with_data(self, client: TestClient, db_session, auth_headers: dict):
        """Récupère l'usage du jour avec des données."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        today = datetime.now(timezone.utc).date()
        usage = AppUsage(
            child_id=child.id,
            package_name="com.netflix.mediaclient",
            app_name="Netflix",
            duration_seconds=3600,
            usage_date=today,
        )
        db_session.add(usage)
        db_session.commit()
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/today", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_seconds"] == 3600
        assert len(data["apps"]) == 1
        assert data["apps"][0]["package_name"] == "com.netflix.mediaclient"


class TestGetWeeklyUsage:
    """Tests pour GET /children/{id}/usage/weekly."""

    def test_get_weekly_seven_days(self, client: TestClient, db_session, auth_headers: dict):
        """Retourne exactement 7 jours, même sans données."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/weekly", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 7
        # Tous les jours sans données doivent avoir total_seconds = 0
        for day in data["days"]:
            assert day["total_seconds"] == 0

    def test_get_weekly_with_data(self, client: TestClient, db_session, auth_headers: dict):
        """Semaine avec des données."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)
        
        db_session.add(AppUsage(child_id=child.id, package_name="com.app1", app_name="App1", duration_seconds=1000, usage_date=today))
        db_session.add(AppUsage(child_id=child.id, package_name="com.app2", app_name="App2", duration_seconds=2000, usage_date=yesterday))
        db_session.commit()
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/weekly", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["days"]) == 7
        assert data["total_seconds"] == 3000


class TestGetDailyUsage:
    """Tests pour GET /children/{id}/usage/daily."""

    def test_get_daily_specific_date(self, client: TestClient, db_session, auth_headers: dict):
        """Récupère l'usage d'une date précise."""
        from nexuscare.models.parent import Parent
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        target_date = date(2025, 5, 1)
        db_session.add(AppUsage(child_id=child.id, package_name="com.spotify.music", app_name="Spotify", duration_seconds=1800, usage_date=target_date))
        db_session.commit()
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/daily?date=2025-05-01", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2025-05-01"
        assert data["total_seconds"] == 1800


class TestGetUsageSummary:
    """Tests pour GET /children/{id}/usage/summary."""

    def test_summary_with_limit(self, client: TestClient, db_session, auth_headers: dict):
        """Résumé avec limite SCREEN_LIMIT."""
        from nexuscare.models.parent import Parent
        
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        today = datetime.now(timezone.utc).date()
        db_session.add(AppUsage(child_id=child.id, package_name="com.game.app", app_name="Game", duration_seconds=3600, usage_date=today))
        
        # Crée une règle SCREEN_LIMIT de 2 heures (7200s) via l'API rules
        rule_data = {
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }
        resp_rule = client.post(f"/api/v1/rules/child/{child.id}", json=rule_data, headers=auth_headers)
        assert resp_rule.status_code == 201
        
        resp = client.get(f"/api/v1/children/{child.id}/usage/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["today_seconds"] == 3600
        assert data["today_limit_seconds"] == 7200
        assert data["percentage_used"] == 50.0
        assert len(data["top_apps"]) == 1


class TestCleanupOldUsage:
    """Tests pour le nettoyage des anciennes données."""

    def test_cleanup_old_usage(self, client: TestClient, db_session, auth_headers: dict):
        """Supprime les entrées de plus de 30 jours."""
        from nexuscare.services import usage_service
        from nexuscare.models.parent import Parent
        
        parent = db_session.query(Parent).first()
        child = Child(parent_id=parent.id, name="Test Child", age=10, profile_tier="PREADOLESCENCE")
        db_session.add(child)
        db_session.commit()
        
        today = datetime.now(timezone.utc).date()
        old_date = today - timedelta(days=31)
        
        # Données récentes (doivent rester)
        db_session.add(AppUsage(child_id=child.id, package_name="com.recent", app_name="Recent", duration_seconds=100, usage_date=today))
        # Données anciennes (doivent être supprimées)
        db_session.add(AppUsage(child_id=child.id, package_name="com.old", app_name="Old", duration_seconds=100, usage_date=old_date))
        db_session.commit()
        
        # Nettoie
        deleted = usage_service.cleanup_old_usage(db_session, days_to_keep=30)
        assert deleted == 1
        
        # Vérifie qu'il reste seulement la donnée récente
        remaining = db_session.query(AppUsage).filter(AppUsage.child_id == child.id).all()
        assert len(remaining) == 1
        assert remaining[0].package_name == "com.recent"


class TestUsageIsolation:
    """Tests d'isolation entre parents."""

    def test_cannot_access_other_parent_child_usage(self, client: TestClient, db_session):
        """Un parent ne peut pas voir l'usage d'un enfant qui n'est pas le sien."""
        from nexuscare.models.parent import Parent
        from nexuscare.core.security import hash_password
        
        # Crée deux parents
        parent1 = Parent(email="p1@test.com", full_name="Parent1", password_hash=hash_password("pass123"))
        parent2 = Parent(email="p2@test.com", full_name="Parent2", password_hash=hash_password("pass123"))
        db_session.add_all([parent1, parent2])
        db_session.commit()
        
        # Enfant du parent2
        child2 = Child(parent_id=parent2.id, name="Test Child", age=8, profile_tier="CHILDHOOD")
        db_session.add(child2)
        db_session.commit()
        
        # Login parent1
        login_resp = client.post("/api/v1/auth/login", json={"email": "p1@test.com", "password": "pass123"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Parent1 essaie de voir l'usage de child2
        resp = client.get(f"/api/v1/children/{child2.id}/usage/today", headers=headers)
        assert resp.status_code == 404
