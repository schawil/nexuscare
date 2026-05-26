"""
Router Children — CRUD profils enfants + liaison appareil.
Préfixe : /api/v1/children
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent
from nexuscare.models.parent import Parent
from nexuscare.schemas.children import (
    ChildCreateRequest,
    ChildResponse,
    ChildUpdateRequest,
    LinkCodeResponse,
    LinkDeviceRequest,
    MessageResponse,
)
from nexuscare.services import children_service

router = APIRouter(prefix="/children", tags=["Enfants"])


@router.get("", response_model=list[ChildResponse], summary="Lister les enfants")
def list_children(
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[ChildResponse]:
    return children_service.list_children(current_parent, db)


@router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED,
             summary="Créer un profil enfant")
def create_child(
    data: ChildCreateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.create_child(data, current_parent, db)


@router.get("/{child_id}", response_model=ChildResponse, summary="Détail d'un enfant")
def get_child(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.get_child(child_id, current_parent, db)


@router.patch("/{child_id}", response_model=ChildResponse, summary="Modifier un enfant")
def update_child(
    child_id: int,
    data: ChildUpdateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.update_child(child_id, data, current_parent, db)


@router.delete("/{child_id}", response_model=MessageResponse, summary="Supprimer un enfant")
def delete_child(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MessageResponse:
    children_service.delete_child(child_id, current_parent, db)
    return MessageResponse(message="Profil enfant supprimé.")


@router.post("/{child_id}/link-code", response_model=LinkCodeResponse,
             summary="Générer un code de liaison")
def generate_link_code(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> LinkCodeResponse:
    return children_service.generate_link_code(child_id, current_parent, db)


@router.post("/{child_id}/link-device", response_model=ChildResponse,
             summary="Lier un appareil Android")
def link_device(
    child_id: int,
    data: LinkDeviceRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> ChildResponse:
    return children_service.link_device(child_id, data.code, data.device_id, current_parent, db)
