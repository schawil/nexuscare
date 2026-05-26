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

_bearer = HTTPBearer(auto_error=False)  # auto_error=False permet de gérer nous-mêmes l'erreur


def get_current_parent(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Parent:
    """
    Dépendance d'authentification.
    Valide le Bearer token JWT et retourne le Parent connecté.
    Utilisé dans toutes les routes protégées : 
    router.get("/...", dependencies=[Depends(get_current_parent)])
    
    Ou avec injection directe :
    def ma_route(current_parent: Parent = Depends(get_current_parent)): ...
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
# Exemple : current_parent: CurrentParentDep = Depends(get_current_parent)
# À définir APRÈS la fonction get_current_parent pour éviter NameError
CurrentParentDep = Annotated[Parent, Depends(get_current_parent)]


def get_current_parent_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Optional[Parent]:
    """
    Dépendance d'authentification optionnelle.
    Retourne le Parent si authentifié, sinon None.
    Utile pour les routes qui fonctionnent aussi bien pour les utilisateurs
    authentifiés que non-authentifiés (ex: liste publique avec options premium).
    """
    if credentials is None:
        return None

    try:
        parent_id = decode_access_token(credentials.credentials)
    except JWTError:
        return None

    parent = db.get(Parent, parent_id)
    return parent