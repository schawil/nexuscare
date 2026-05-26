"""
Core module — Configuration, sécurité, dépendances et base de données.
"""
from nexuscare.core.config import settings
from nexuscare.core.database import Base, get_db, engine
from nexuscare.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    verify_password,
)
from nexuscare.core.dependencies import (
    get_current_parent,
    get_current_parent_optional,
    CurrentParentDep,
)

__all__ = [
    "settings",
    "Base",
    "get_db",
    "engine",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "hash_password",
    "hash_token",
    "verify_password",
    "get_current_parent",
    "get_current_parent_optional",
    "CurrentParentDep",
]