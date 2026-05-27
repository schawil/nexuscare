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
    create_device_token,
    hash_password,
    hash_token,
    verify_password,
)
from nexuscare.models.parent import Parent
from nexuscare.models.child import Child
from nexuscare.models.refresh_token import RefreshToken
from nexuscare.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    ParentResponse,
    TokenResponse,
    DeviceLoginRequest,
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
    # Pas besoin de refresh car expire_on_commit=False

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
    # Pas besoin de refresh car expire_on_commit=False

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
    Implémente une vérification à temps constant pour éviter les timing attacks.
    """
    _generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email ou mot de passe incorrect.",
    )

    parent = db.query(Parent).filter(Parent.email == data.email).first()
    
    # Hash fictif valide pour la vérification à temps constant (même si l'email n'existe pas)
    _dummy_hash = "$2b$12$LqLiVvH8hQJzK5zJxZ9Yp.vWqN3X5R7T9U1V3W5X7Y9Z1A3B5C7D9"
    
    if parent is None:
        # Vérifie quand même un hash fictif pour éviter le timing attack
        verify_password("dummy", _dummy_hash)
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


def device_login(data: DeviceLoginRequest, db: Session) -> dict:
    """
    Authentifie un appareil enfant via son device_id.
    Retourne un token JWT de type "device" sans refresh token.
    Lève HTTP 404 si le device_id n'est pas lié à un enfant.
    """
    # Cherche un enfant avec ce device_id
    child = db.query(Child).filter(Child.device_id == data.device_id).first()
    
    if child is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appareil non lié. Veuillez saisir le code de liaison fourni par le parent.",
        )
    
    # Crée un token device (pas de refresh token pour les enfants)
    access_token = create_device_token(child.id, data.device_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "child_id": child.id,
        "profile_tier": child.profile_tier,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }