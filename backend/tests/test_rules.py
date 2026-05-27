"""
Tests d'intégration — Module Rules (20 tests au total)
Utilise les fixtures partagées définies dans conftest.py
"""
import pytest
from fastapi.testclient import TestClient


# ==================== Tests de création de règles ====================

class TestCreateRule:
    """Tests pour la création de règles."""

    def test_create_screen_limit(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle SCREEN_LIMIT."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "SCREEN_LIMIT"
        assert body["config"]["daily_limit_seconds"] == 7200
        assert body["is_active"] is True

    def test_create_app_block(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle APP_BLOCK."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "APP_BLOCK",
            "config": {"package_name": "com.tiktok.android", "app_name": "TikTok"},
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "APP_BLOCK"
        assert body["config"]["package_name"] == "com.tiktok.android"

    def test_create_app_time_limit(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle APP_TIME_LIMIT."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "APP_TIME_LIMIT",
            "config": {
                "package_name": "com.instagram.android",
                "daily_limit_seconds": 1800,
                "app_name": "Instagram"
            },
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "APP_TIME_LIMIT"
        assert body["config"]["daily_limit_seconds"] == 1800

    def test_create_time_slot(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle TIME_SLOT."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "TIME_SLOT",
            "config": {
                "slot_name": "NIGHT",
                "days_of_week": [1, 2, 3, 4, 5],
                "start_time": "21:00",
                "end_time": "07:00",
                "allowed_packages": ["com.whatsapp"]
            },
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["rule_type"] == "TIME_SLOT"
        assert body["config"]["slot_name"] == "NIGHT"

    def test_create_rule_invalid_config(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle avec configuration invalide."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": -100},  # Négatif invalide
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_rule_invalid_days(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Créer une règle TIME_SLOT avec jours invalides."""
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "TIME_SLOT",
            "config": {
                "slot_name": "WEEKEND",
                "days_of_week": [0, 8],  # Jours hors plage
                "start_time": "10:00",
                "end_time": "12:00",
            },
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_create_rule_nonexistent_child(self, client: TestClient, auth_headers: dict):
        """Créer une règle pour un enfant inexistant."""
        resp = client.post("/api/v1/rules", json={
            "child_id": 99999,
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_create_rule_other_parent_child(self, client: TestClient, created_child: dict):
        """Essayer de créer une règle pour l'enfant d'un autre parent."""
        # Crée un deuxième parent
        resp_reg = client.post("/api/v1/auth/register", json={
            "full_name": "Autre Parent",
            "email": "autre@test.com",
            "password": "motdepasse123",
        })
        assert resp_reg.status_code == 201
        
        resp_login = client.post("/api/v1/auth/login", json={
            "email": "autre@test.com",
            "password": "motdepasse123",
        })
        assert resp_login.status_code == 200
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}
        
        # Essaie de créer une règle pour l'enfant du premier parent
        resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=other_headers)
        assert resp.status_code == 404


# ==================== Tests de liste de règles ====================

class TestListRules:
    """Tests pour la liste des règles."""

    def test_list_empty(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Lister les règles d'un enfant sans règles."""
        resp = client.get(f"/api/v1/rules/child/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_multiple(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Lister plusieurs règles d'un enfant."""
        # Crée 3 règles avec des configs distinctes
        rules_to_create = [
            ("SCREEN_LIMIT", {"daily_limit_seconds": 7200}),
            ("APP_BLOCK", {"package_name": "com.app1.android", "app_name": "App1"}),
            ("APP_TIME_LIMIT", {"package_name": "com.app2.android", "daily_limit_seconds": 1800, "app_name": "App2"}),
        ]
        
        for rule_type, config in rules_to_create:
            resp = client.post("/api/v1/rules", json={
                "child_id": created_child["id"],
                "rule_type": rule_type,
                "config": config,
                "is_active": True,
            }, headers=auth_headers)
            assert resp.status_code == 201, f"Failed to create {rule_type}: {resp.json()}"
        
        resp = client.get(f"/api/v1/rules/child/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) == 3

    def test_list_isolation_between_parents(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Vérifier l'isolation entre parents."""
        # Crée une règle pour le premier enfant
        client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        
        # Crée un deuxième parent avec son propre enfant
        resp_reg = client.post("/api/v1/auth/register", json={
            "full_name": "Autre Parent",
            "email": "autre2@test.com",
            "password": "motdepasse123",
        })
        assert resp_reg.status_code == 201
        
        resp_login = client.post("/api/v1/auth/login", json={
            "email": "autre2@test.com",
            "password": "motdepasse123",
        })
        assert resp_login.status_code == 200
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}
        
        resp_child = client.post("/api/v1/children", json={"name": "Autre Enfant", "age": 10}, headers=other_headers)
        assert resp_child.status_code == 201
        other_child_id = resp_child.json()["id"]
        
        # Crée une règle pour le deuxième enfant
        client.post("/api/v1/rules", json={
            "child_id": other_child_id,
            "rule_type": "APP_BLOCK",
            "config": {"package_name": "com.facebook.katana", "app_name": "Facebook"},
            "is_active": True,
        }, headers=other_headers)
        
        # Vérifie que le premier parent ne voit que sa règle
        resp = client.get(f"/api/v1/rules/child/{created_child['id']}", headers=auth_headers)
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) == 1
        assert rules[0]["rule_type"] == "SCREEN_LIMIT"


# ==================== Tests de récupération de règle ====================

class TestGetRule:
    """Tests pour récupérer une règle spécifique."""

    def test_get_existing(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Récupérer une règle existante."""
        # Crée une règle
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 5400},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Récupère la règle
        resp = client.get(f"/api/v1/rules/{rule_id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == rule_id
        assert body["config"]["daily_limit_seconds"] == 5400

    def test_get_not_found(self, client: TestClient, auth_headers: dict):
        """Récupérer une règle inexistante."""
        resp = client.get("/api/v1/rules/99999", headers=auth_headers)
        assert resp.status_code == 404


# ==================== Tests de modification de règle ====================

class TestUpdateRule:
    """Tests pour modifier une règle."""

    def test_update_config(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Modifier la configuration d'une règle."""
        # Crée une règle
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 3600},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Met à jour la config
        resp = client.patch(f"/api/v1/rules/{rule_id}", json={
            "config": {"daily_limit_seconds": 10800}
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["config"]["daily_limit_seconds"] == 10800

    def test_update_is_active(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Modifier l'état actif d'une règle."""
        # Crée une règle active
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "APP_BLOCK",
            "config": {"package_name": "com.snapchat.android", "app_name": "Snapchat"},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Désactive la règle
        resp = client.patch(f"/api/v1/rules/{rule_id}", json={
            "is_active": False
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is False

    def test_partial_update(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Mise à jour partielle (seulement config ou seulement is_active)."""
        # Crée une règle
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "TIME_SLOT",
            "config": {
                "slot_name": "STUDY",
                "days_of_week": [1, 3, 5],
                "start_time": "14:00",
                "end_time": "16:00",
            },
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Met à jour seulement is_active
        resp = client.patch(f"/api/v1/rules/{rule_id}", json={
            "is_active": False
        }, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_active"] is False
        assert body["config"]["slot_name"] == "STUDY"  # Config inchangée


# ==================== Tests de toggle ====================

class TestToggleRule:
    """Tests pour activer/désactiver une règle."""

    def test_toggle_off(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Désactiver une règle."""
        # Crée une règle active
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Désactive
        resp = client.post(f"/api/v1/rules/{rule_id}/toggle?is_active=false", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_toggle_on(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Réactiver une règle."""
        # Crée une règle inactive
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "APP_BLOCK",
            "config": {"package_name": "com.discord", "app_name": "Discord"},
            "is_active": False,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Réactive
        resp = client.post(f"/api/v1/rules/{rule_id}/toggle?is_active=true", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True


# ==================== Tests de suppression ====================

class TestDeleteRule:
    """Tests pour supprimer une règle."""

    def test_delete(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Supprimer une règle."""
        # Crée une règle
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Supprime
        resp = client.delete(f"/api/v1/rules/{rule_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Règle supprimée."
        
        # Vérifie que la règle n'existe plus
        get_resp = client.get(f"/api/v1/rules/{rule_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_not_found(self, client: TestClient, auth_headers: dict):
        """Supprimer une règle inexistante."""
        resp = client.delete("/api/v1/rules/99999", headers=auth_headers)
        assert resp.status_code == 404


# ==================== Tests d'isolation et sécurité ====================

class TestRuleIsolation:
    """Tests d'isolation entre parents."""

    def test_cannot_access_other_parent_rule(self, client: TestClient, auth_headers: dict, created_child: dict):
        """Un parent ne peut pas accéder aux règles d'un autre parent."""
        # Crée une règle
        create_resp = client.post("/api/v1/rules", json={
            "child_id": created_child["id"],
            "rule_type": "SCREEN_LIMIT",
            "config": {"daily_limit_seconds": 7200},
            "is_active": True,
        }, headers=auth_headers)
        rule_id = create_resp.json()["id"]
        
        # Crée un autre parent
        resp_reg = client.post("/api/v1/auth/register", json={
            "full_name": "Espion",
            "email": "espion@test.com",
            "password": "motdepasse123",
        })
        resp_login = client.post("/api/v1/auth/login", json={
            "email": "espion@test.com",
            "password": "motdepasse123",
        })
        spy_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}
        
        # Essaie d'accéder à la règle
        resp = client.get(f"/api/v1/rules/{rule_id}", headers=spy_headers)
        assert resp.status_code == 404

    def test_requires_auth(self, client: TestClient):
        """Les endpoints rules nécessitent une authentification."""
        resp = client.get("/api/v1/rules/child/1")
        assert resp.status_code == 401
        
        resp = client.post("/api/v1/rules", json={})
        assert resp.status_code == 401
