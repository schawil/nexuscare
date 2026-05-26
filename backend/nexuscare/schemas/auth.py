"""
Schémas Pydantic v2 — Authentification
Valident et sérialisent toutes les données entrantes/sortantes de l'API Auth.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Requêtes (entrées) ───────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100, examples=["Sandrine Dupont"])
    email: EmailStr = Field(examples=["sandrine@example.com"])
    password: str = Field(min_length=8, max_length=128, examples=["motdepasse123"])

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Vérifie qu'il y a au moins un chiffre et une lettre."""
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une lettre.")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["sandrine@example.com"])
    password: str = Field(min_length=1, examples=["motdepasse123"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


# ─── Réponses (sorties) ───────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes avant expiration de l'access token


class ParentResponse(BaseModel):
    id: int
    email: str
    full_name: str

    model_config = {"from_attributes": True}


class RegisterResponse(BaseModel):
    parent: ParentResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    message: str