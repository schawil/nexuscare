"""
Service Rules — logique métier isolée des routes FastAPI.
Gère le CRUD des règles de contrôle parental.
"""
import json
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from nexuscare.models.rule import Rule
from nexuscare.models.child import Child
from nexuscare.models.parent import Parent
from nexuscare.schemas.rules import (
    RuleCreateRequest,
    RuleUpdateRequest,
    RuleResponse,
)


def _get_rule_or_404(rule_id: int, parent: Parent, db: Session) -> Rule:
    """Récupère une règle ou lève une 404 si inexistante ou non accessible."""
    rule = db.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle introuvable.")
    
    # Vérifie que le parent a accès à cette règle via l'enfant
    child = db.get(Child, rule.child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Règle introuvable.")
    
    return rule


def _get_child_or_404(child_id: int, parent: Parent, db: Session) -> Child:
    """Récupère un enfant ou lève une 404 si inexistant ou non accessible."""
    child = db.get(Child, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    return child


def list_rules_for_child(child_id: int, parent: Parent, db: Session) -> list[RuleResponse]:
    """Liste toutes les règles d'un enfant."""
    # Vérifie que le parent a accès à cet enfant
    _get_child_or_404(child_id, parent, db)
    
    rules = (
        db.query(Rule)
        .filter(Rule.child_id == child_id)
        .order_by(Rule.created_at.asc())
        .all()
    )
    return [RuleResponse.from_orm_rule(r) for r in rules]


def create_rule(data: RuleCreateRequest, parent: Parent, db: Session) -> RuleResponse:
    """Crée une nouvelle règle pour un enfant."""
    # Vérifie que le parent a accès à cet enfant
    child = _get_child_or_404(data.child_id, parent, db)
    
    # Sérialise la configuration en JSON
    config_json = json.dumps(data.config)
    
    rule = Rule(
        child_id=data.child_id,
        rule_type=data.rule_type,
        config=config_json,
        is_active=data.is_active,
    )
    db.add(rule)
    db.commit()
    # Pas besoin de refresh car expire_on_commit=False
    
    return RuleResponse.from_orm_rule(rule)


def get_rule(rule_id: int, parent: Parent, db: Session) -> RuleResponse:
    """Récupère les détails d'une règle."""
    rule = _get_rule_or_404(rule_id, parent, db)
    return RuleResponse.from_orm_rule(rule)


def update_rule(rule_id: int, data: RuleUpdateRequest, parent: Parent, db: Session) -> RuleResponse:
    """Met à jour une règle (config et/ou is_active)."""
    rule = _get_rule_or_404(rule_id, parent, db)
    
    if data.config is not None:
        # Valide la configuration selon le type de règle
        from nexuscare.schemas.rules import (
            ScreenLimitConfig, AppBlockConfig, AppTimeLimitConfig, TimeSlotConfig
        )
        try:
            if rule.rule_type == "SCREEN_LIMIT":
                ScreenLimitConfig(**data.config)
            elif rule.rule_type == "APP_BLOCK":
                AppBlockConfig(**data.config)
            elif rule.rule_type == "APP_TIME_LIMIT":
                AppTimeLimitConfig(**data.config)
            elif rule.rule_type == "TIME_SLOT":
                TimeSlotConfig(**data.config)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Configuration invalide: {str(e)}",
            )
        rule.config = json.dumps(data.config)
    
    if data.is_active is not None:
        rule.is_active = data.is_active
    
    db.commit()
    # Pas besoin de refresh car expire_on_commit=False
    
    return RuleResponse.from_orm_rule(rule)


def toggle_rule(rule_id: int, is_active: bool, parent: Parent, db: Session) -> RuleResponse:
    """Active ou désactive une règle."""
    rule = _get_rule_or_404(rule_id, parent, db)
    rule.is_active = is_active
    db.commit()
    # Pas besoin de refresh car expire_on_commit=False
    return RuleResponse.from_orm_rule(rule)


def delete_rule(rule_id: int, parent: Parent, db: Session) -> None:
    """Supprime une règle."""
    rule = _get_rule_or_404(rule_id, parent, db)
    db.delete(rule)
    db.commit()
