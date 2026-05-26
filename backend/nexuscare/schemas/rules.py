"""
Schémas Pydantic v2 — Module Rules
Aucun import SQLAlchemy ici — uniquement Pydantic BaseModel.
"""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
import json


class RuleConfigBase(BaseModel):
    """Classe de base pour les configurations de règles."""
    pass


class ScreenLimitConfig(RuleConfigBase):
    """Configuration pour SCREEN_LIMIT."""
    daily_limit_seconds: int = Field(ge=0, examples=[7200])


class AppBlockConfig(RuleConfigBase):
    """Configuration pour APP_BLOCK."""
    package_name: str = Field(min_length=1, max_length=255, examples=["com.tiktok.android"])
    app_name: str = Field(min_length=1, max_length=100, examples=["TikTok"])


class AppTimeLimitConfig(RuleConfigBase):
    """Configuration pour APP_TIME_LIMIT."""
    package_name: str = Field(min_length=1, max_length=255, examples=["com.instagram.android"])
    daily_limit_seconds: int = Field(ge=0, examples=[1800])
    app_name: str = Field(default="", max_length=100, examples=["Instagram"])


class TimeSlotConfig(RuleConfigBase):
    """Configuration pour TIME_SLOT."""
    slot_name: str = Field(min_length=1, max_length=50, examples=["NIGHT"])
    days_of_week: list[int] = Field(default_factory=list)  # 1=Lundi, 7=Dimanche
    start_time: str = Field(pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", examples=["21:00"])
    end_time: str = Field(pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", examples=["07:00"])
    allowed_packages: list[str] = Field(default_factory=list)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        if not all(1 <= day <= 7 for day in v):
            raise ValueError("Les jours doivent être entre 1 (Lundi) et 7 (Dimanche).")
        return v


# Type union pour toutes les configurations
RuleConfigUnion = ScreenLimitConfig | AppBlockConfig | AppTimeLimitConfig | TimeSlotConfig


class RuleCreateRequest(BaseModel):
    """Requête pour créer une règle."""
    child_id: int = Field(gt=0, examples=[1])
    rule_type: Literal["SCREEN_LIMIT", "APP_BLOCK", "APP_TIME_LIMIT", "TIME_SLOT"]
    config: dict = Field(..., description="Configuration JSON selon le type de règle")
    is_active: bool = True

    @model_validator(mode="after")
    def validate_config(self):
        """Valide la configuration selon le type de règle."""
        try:
            if self.rule_type == "SCREEN_LIMIT":
                ScreenLimitConfig(**self.config)
            elif self.rule_type == "APP_BLOCK":
                AppBlockConfig(**self.config)
            elif self.rule_type == "APP_TIME_LIMIT":
                AppTimeLimitConfig(**self.config)
            elif self.rule_type == "TIME_SLOT":
                TimeSlotConfig(**self.config)
        except Exception as e:
            raise ValueError(f"Configuration invalide pour {self.rule_type}: {str(e)}")
        return self


class RuleUpdateRequest(BaseModel):
    """Requête pour mettre à jour une règle."""
    config: dict | None = Field(default=None, description="Nouvelle configuration JSON")
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if self.config is None and self.is_active is None:
            raise ValueError("Au moins un champ (config ou is_active) doit être fourni.")
        return self


class RuleToggleRequest(BaseModel):
    """Requête pour activer/désactiver une règle."""
    is_active: bool


class RuleResponse(BaseModel):
    """Réponse pour une règle."""
    id: int
    child_id: int
    rule_type: Literal["SCREEN_LIMIT", "APP_BLOCK", "APP_TIME_LIMIT", "TIME_SLOT"]
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_rule(cls, rule: object) -> "RuleResponse":
        """Crée une réponse depuis un objet SQLAlchemy Rule."""
        import json
        return cls(
            id=rule.id,  # type: ignore[attr-defined]
            child_id=rule.child_id,  # type: ignore[attr-defined]
            rule_type=rule.rule_type,  # type: ignore[attr-defined]
            config=json.loads(rule.config),  # type: ignore[attr-defined]
            is_active=rule.is_active,  # type: ignore[attr-defined]
            created_at=rule.created_at,  # type: ignore[attr-defined]
            updated_at=rule.updated_at,  # type: ignore[attr-defined]
        )


class MessageResponse(BaseModel):
    """Réponse message simple."""
    message: str
