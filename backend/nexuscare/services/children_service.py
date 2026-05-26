"""
Service Children — logique métier isolée des routes FastAPI.
"""
import secrets
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from nexuscare.core.security import hash_token
from nexuscare.models.child import Child
from nexuscare.models.parent import Parent
from nexuscare.schemas.children import (
    ChildCreateRequest,
    ChildUpdateRequest,
    ChildResponse,
    LinkCodeResponse,
)

_LINK_CODE_TTL_SECONDS = 600


def _get_child_or_404(child_id: int, parent: Parent, db: Session) -> Child:
    child = db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    return child


def list_children(parent: Parent, db: Session) -> list[ChildResponse]:
    children = (
        db.query(Child)
        .filter(Child.parent_id == parent.id)
        .order_by(Child.created_at.asc())
        .all()
    )
    return [ChildResponse.from_orm_child(c) for c in children]


def create_child(data: ChildCreateRequest, parent: Parent, db: Session) -> ChildResponse:
    try:
        tier = Child.compute_tier(data.age)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    child = Child(parent_id=parent.id, name=data.name, age=data.age, profile_tier=tier)
    db.add(child)
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)


def get_child(child_id: int, parent: Parent, db: Session) -> ChildResponse:
    return ChildResponse.from_orm_child(_get_child_or_404(child_id, parent, db))


def update_child(child_id: int, data: ChildUpdateRequest, parent: Parent, db: Session) -> ChildResponse:
    child = _get_child_or_404(child_id, parent, db)
    if data.name is not None:
        child.name = data.name
    if data.age is not None:
        try:
            child.age = data.age
            child.profile_tier = Child.compute_tier(data.age)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)


def delete_child(child_id: int, parent: Parent, db: Session) -> None:
    child = _get_child_or_404(child_id, parent, db)
    db.delete(child)
    db.commit()


def generate_link_code(child_id: int, parent: Parent, db: Session) -> LinkCodeResponse:
    child = _get_child_or_404(child_id, parent, db)
    raw_code = str(secrets.randbelow(1_000_000)).zfill(6)
    child.link_code_hash = hash_token(raw_code)
    db.commit()
    return LinkCodeResponse(child_id=child.id, code=raw_code, expires_in=_LINK_CODE_TTL_SECONDS)


def link_device(child_id: int, code: str, device_id: str, parent: Parent, db: Session) -> ChildResponse:
    child = _get_child_or_404(child_id, parent, db)
    if child.link_code_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun code de liaison actif. Génère-en un nouveau.",
        )
    if hash_token(code) != child.link_code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code de liaison incorrect.")
    existing = db.query(Child).filter(Child.device_id == device_id).first()
    if existing and existing.id != child_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cet appareil est déjà lié à un autre profil.")
    child.device_id = device_id
    child.link_code_hash = None
    db.commit()
    db.refresh(child)
    return ChildResponse.from_orm_child(child)
