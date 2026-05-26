"""
Router Rules — CRUD des règles de contrôle parental.
Préfixe : /api/v1/rules
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent
from nexuscare.models.parent import Parent
from nexuscare.schemas.rules import (
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleResponse,
    MessageResponse,
)
from nexuscare.services import rules_service

router = APIRouter(prefix="/rules", tags=["Règles"])


@router.get("/child/{child_id}", response_model=list[RuleResponse], summary="Lister les règles d'un enfant")
def list_rules(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> list[RuleResponse]:
    """Liste toutes les règles configurées pour un enfant donné."""
    return rules_service.list_rules_for_child(child_id, current_parent, db)


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED,
             summary="Créer une règle")
def create_rule(
    data: RuleCreateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Crée une nouvelle règle de contrôle pour un enfant."""
    return rules_service.create_rule(data, current_parent, db)


@router.get("/{rule_id}", response_model=RuleResponse, summary="Détail d'une règle")
def get_rule(
    rule_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Récupère les détails d'une règle spécifique."""
    return rules_service.get_rule(rule_id, current_parent, db)


@router.patch("/{rule_id}", response_model=RuleResponse, summary="Modifier une règle")
def update_rule(
    rule_id: int,
    data: RuleUpdateRequest,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Met à jour la configuration et/ou l'état actif d'une règle."""
    return rules_service.update_rule(rule_id, data, current_parent, db)


@router.post("/{rule_id}/toggle", response_model=RuleResponse, summary="Activer/Désactiver une règle")
def toggle_rule(
    rule_id: int,
    is_active: bool,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> RuleResponse:
    """Active ou désactive une règle sans modifier sa configuration."""
    return rules_service.toggle_rule(rule_id, is_active, current_parent, db)


@router.delete("/{rule_id}", response_model=MessageResponse, summary="Supprimer une règle")
def delete_rule(
    rule_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Supprime définitivement une règle."""
    rules_service.delete_rule(rule_id, current_parent, db)
    return MessageResponse(message="Règle supprimée.")
