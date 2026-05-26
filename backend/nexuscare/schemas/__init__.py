"""
Export centralisé des schémas Pydantic pour une importation simplifiée.
Permet : from nexuscare.schemas import TokenResponse, ParentResponse, etc.
"""
from nexuscare.schemas.auth import (
    LoginRequest,
    MessageResponse,
    ParentResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)

__all__ = [
    "LoginRequest",
    "MessageResponse",
    "ParentResponse",
    "RefreshRequest",
    "RegisterRequest",
    "RegisterResponse",
    "TokenResponse",
]