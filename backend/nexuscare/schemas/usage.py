"""
Schémas Pydantic v2 — Module Usage
Aucun import SQLAlchemy ici — uniquement Pydantic BaseModel.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UsageEntryCreate(BaseModel):
    """Entrée d'utilisation individuelle envoyée par l'APK Enfant."""
    package_name: str = Field(min_length=1, max_length=255, examples=["com.tiktok.android"])
    app_name: str = Field(min_length=1, max_length=100, examples=["TikTok"])
    duration_seconds: int = Field(ge=0, examples=[300])
    usage_date: date = Field(..., description="Date de l'usage au format YYYY-MM-DD")

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v > 86400:  # Max 24h en secondes
            raise ValueError("La durée ne peut pas dépasser 86400 secondes (24h).")
        return v


class UsageReportRequest(BaseModel):
    """Requête pour envoyer un rapport d'utilisation complet."""
    usages: list[UsageEntryCreate] = Field(..., min_length=1, max_length=100)


class UsageEntryResponse(BaseModel):
    """Réponse pour une entrée d'utilisation individuelle."""
    id: int
    child_id: int
    package_name: str
    app_name: str
    duration_seconds: int
    usage_date: date
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DailyUsageSummary(BaseModel):
    """Résumé de l'utilisation pour une journée, groupé par application."""
    package_name: str
    app_name: str
    total_seconds: int
    percentage_of_day: float = Field(..., description="Pourcentage du temps total de la journée")

    model_config = {"from_attributes": True}


class DailyUsageResponse(BaseModel):
    """Réponse pour l'usage détaillé d'une journée."""
    date: date
    total_seconds: int
    entries: list[DailyUsageSummary]

    @classmethod
    def from_entries(cls, usage_date: date, entries: list[dict]) -> "DailyUsageResponse":
        total = sum(e["total_seconds"] for e in entries)
        return cls(
            date=usage_date,
            total_seconds=total,
            entries=[
                DailyUsageSummary(
                    package_name=e["package_name"],
                    app_name=e["app_name"],
                    total_seconds=e["total_seconds"],
                    percentage_of_day=round((e["total_seconds"] / total * 100), 2) if total > 0 else 0.0
                )
                for e in entries
            ]
        )


class WeeklyUsageItem(BaseModel):
    """Item pour le résumé hebdomadaire."""
    date: date
    total_seconds: int


class WeeklyUsageResponse(BaseModel):
    """Réponse pour l'usage des 7 derniers jours."""
    days: list[WeeklyUsageItem]
    total_seconds: int
    average_seconds_per_day: float

    @classmethod
    def from_days(cls, days: list[dict]) -> "WeeklyUsageResponse":
        total = sum(d["total_seconds"] for d in days)
        avg = total / len(days) if days else 0.0
        return cls(
            days=[WeeklyUsageItem(**d) for d in days],
            total_seconds=total,
            average_seconds_per_day=round(avg, 2)
        )


class MessageResponse(BaseModel):
    """Réponse message simple."""
    message: str
