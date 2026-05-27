"""
Dépendances FastAPI réutilisables.
Injectées dans les routes via Depends() pour centraliser l'authentification.
"""
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from nexuscare.core.database import get_db
from nexuscare.core.security import decode_access_token
from nexuscare.models.parent import Parent
from nexuscare.models.child import Child

_bearer = HTTPBearer(auto_error=False)  # auto_error=False permet de gérer nous-mêmes l'erreur


def _decode_token_and_validate_type(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
    expected_type: str,
) -> tuple[int, str]:
    """
    Décode le token JWT et valide son type.
    Retourne (subject_id, token_type) si valide.
    Lève HTTPException si invalide.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        from jose import jwt
        from nexuscare.core.config import settings
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    token_type = payload.get("type")
    if token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Type de token invalide. Attendu: {expected_type}, Reçu: {token_type}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception

    return int(sub), token_type


def get_current_parent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Parent:
    """
    Dépendance d'authentification parent.
    Valide le Bearer token JWT (type="access") et retourne le Parent connecté.
    Utilisé dans toutes les routes protégées parent.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        parent_id = decode_access_token(credentials.credentials)
    except JWTError:
        raise credentials_exception

    parent = db.get(Parent, parent_id)
    if parent is None:
        raise credentials_exception

    return parent


# Type annoté pour réutiliser la dépendance facilement
CurrentParentDep = Annotated[Parent, Depends(get_current_parent)]


def get_current_child(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Child:
    """
    Dépendance d'authentification enfant (appareil).
    Valide le Bearer token JWT (type="device") et retourne le Child connecté.
    Utilisé dans les routes appelées par l'APK Enfant.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token enfant invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    try:
        from jose import jwt
        from nexuscare.core.config import settings
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    token_type = payload.get("type")
    if token_type != "device":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Type de token invalide. Attendu: device, Reçu: {token_type}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    child_id = payload.get("sub")
    if child_id is None:
        raise credentials_exception

    child = db.get(Child, int(child_id))
    if child is None:
        raise credentials_exception

    return child


# Type annoté pour réutiliser la dépendance facilement
CurrentChildDep = Annotated[Child, Depends(get_current_child)]


def get_current_parent_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[Parent]:
    """
    Dépendance d'authentification optionnelle.
    Retourne le Parent si authentifié, sinon None.
    """
    if credentials is None:
        return None

    try:
        parent_id = decode_access_token(credentials.credentials)
    except JWTError:
        return None

    parent = db.get(Parent, parent_id)
    return parent