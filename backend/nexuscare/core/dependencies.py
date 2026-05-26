"""
Dépendances FastAPI réutilisables.
Injectées dans les routes via Depends() pour centraliser l'authentification.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from nexuscare.core.database import get_db
from nexuscare.core.security import decode_access_token
from nexuscare.models.parent import Parent

_bearer = HTTPBearer()


def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Parent:
    """
    Dépendance d'authentification.
    Valide le Bearer token JWT et retourne le Parent connecté.
    Utilisé dans toutes les routes protégées : router.get("/...", dependencies=[Depends(get_current_parent)])
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        parent_id = decode_access_token(credentials.credentials)
    except JWTError:
        raise credentials_exception

    parent = db.get(Parent, parent_id)
    if parent is None:
        raise credentials_exception

    return parent