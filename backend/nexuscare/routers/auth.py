"""
Router Auth — endpoints publics d'authentification.
Préfixe : /api/v1/auth
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent
from nexuscare.models.parent import Parent
from nexuscare.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    ParentResponse,
)
from nexuscare.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte parent",
)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    """
    Crée un compte parent et retourne les tokens d'accès.
    - Vérifie que l'email n'est pas déjà utilisé (HTTP 409)
    - Hash le mot de passe avec bcrypt
    - Retourne access_token + refresh_token
    """
    return auth_service.register(data, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Connexion parent",
)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Authentifie un parent et retourne les tokens.
    Message d'erreur générique pour ne pas révéler si c'est l'email
    ou le mot de passe qui est incorrect.
    """
    return auth_service.login(data, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renouveler l'access token",
)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Échange un refresh token valide contre un nouvel access token.
    Rotation automatique : l'ancien refresh token est révoqué,
    un nouveau est émis.
    """
    return auth_service.refresh(data.refresh_token, db)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Déconnexion",
)
def logout(data: RefreshRequest, db: Session = Depends(get_db)) -> MessageResponse:
    """
    Révoque le refresh token côté serveur.
    Opération idempotente : un double logout ne provoque pas d'erreur.
    """
    auth_service.logout(data.refresh_token, db)
    return MessageResponse(message="Déconnexion réussie.")


@router.get(
    "/me",
    response_model=ParentResponse,
    summary="Profil du parent connecté",
)
def me(current_parent: Parent = Depends(get_current_parent)) -> ParentResponse:
    """
    Retourne le profil du parent authentifié.
    Utile pour valider un access token côté mobile.
    """
    return ParentResponse.model_validate(current_parent)