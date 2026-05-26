"""
Export centralisé des services pour une importation simplifiée.
Permet : from nexuscare.services import auth_service, children_service, etc.
"""
from nexuscare.services import auth_service
from nexuscare.services import children_service

__all__ = [
    "auth_service",
    "children_service",
]