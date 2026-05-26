"""
Service d'authentification — logique métier isolée des routes FastAPI.
Pattern Service Layer : les routers délèguent ici, les tests unitaires testent ici.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from nexuscare.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from nexuscare.models.parent import Parent
from nexuscare.models.refresh_token import RefreshToken
from nexuscare.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ParentResponse,
    TokenResponse,
)
from nexuscare.core.config import settings


def _build_token_response(parent: Parent, db: Session) -> TokenResponse:
    """
    Crée access + refresh token, persiste le refresh token en base.
    Factorisation pour register et login.
    """
    access_token = create_access_token(parent.id)
    raw_refresh, expires_at = create_refresh_token()

    db_refresh = RefreshToken(
        parent_id=parent.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
    )
    db.add(db_refresh)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def register(data: RegisterRequest, db: Session) -> RegisterResponse:
    """
    Crée un nouveau compte parent.
    Lève HTTP 409 si l'email est déjà utilisé.
    """
    existing = db.query(Parent).filter(Parent.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte avec cet email existe déjà.",
        )

    parent = Parent(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
    )
    db.add(parent)
    db.commit()
    db.refresh(parent)

    tokens = _build_token_response(parent, db)

    return RegisterResponse(
        parent=ParentResponse.model_validate(parent),
        tokens=tokens,
    )


def login(data: LoginRequest, db: Session) -> TokenResponse:
    """
    Authentifie un parent.
    Lève HTTP 401 avec un message générique pour ne pas révéler
    si c'est l'email ou le mot de passe qui est incorrect (sécurité).
    """
    _generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou mot de passe incorrect.",
    )

    parent = db.query(Parent).filter(Parent.email == data.email).first()
    if parent is None:
        # Vérifie quand même un hash fictif pour éviter le timing attack
        verify_password("dummy", "$2b$12$dummyhashtopreventtimingattacks000000000000000000000000")
        raise _generic_error

    if not verify_password(data.password, parent.password_hash):
        raise _generic_error

    return _build_token_response(parent, db)


def refresh(raw_token: str, db: Session) -> TokenResponse:
    """
    Renouvelle l'access token à partir d'un refresh token valide.
    Implémente la rotation : l'ancien refresh token est révoqué,
    un nouveau est émis (One-Time Use).
    """
    token_hash = hash_token(raw_token)

    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked.is_(False),
        )
        .first()
    )

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou révoqué.",
        )

    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db_token.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expiré. Veuillez vous reconnecter.",
        )

    # Révocation de l'ancien token (rotation)
    db_token.is_revoked = True
    db.commit()

    parent = db.get(Parent, db_token.parent_id)
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte introuvable.",
        )

    return _build_token_response(parent, db)


def logout(raw_token: str, db: Session) -> None:
    """
    Révoque le refresh token (logout côté serveur).
    Si le token n'existe pas ou est déjà révoqué, on ne lève pas d'erreur
    (opération idempotente — double logout = pas de crash).
    """
    token_hash = hash_token(raw_token)
    db_token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .first()
    )
    if db_token and not db_token.is_revoked:
        db_token.is_revoked = True
        db.commit()
        