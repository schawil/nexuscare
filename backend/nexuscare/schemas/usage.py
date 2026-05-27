"""
Schémas Pydantic v2 — Usage (temps d'écran par application)
Valident et sérialisent toutes les données entrantes/sortantes de l'API Usage.
"""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Requêtes (entrées) ───────────────────────────────────────────────────────

class UsageEntry(BaseModel):
    """Une entrée d'usage pour une application."""
    package_name: str = Field(min_length=1, max_length=255, examples=["com.tiktok.android"])
    app_name: str = Field(min_length=1, max_length=100, examples=["TikTok"])
    duration_seconds: int = Field(ge=0, le=86400, examples=[3600])
    usage_date: date = Field(examples=["2025-05-14"])

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v < 0:
            raise ValueError("La durée ne peut pas être négative.")
        return v


class UsageReportRequest(BaseModel):
    """
    Rapport d'usage envoyé par l'APK Enfant.
    Contient une liste d'entrées pour plusieurs applications.
    """
    usages: List[UsageEntry] = Field(min_length=1, max_length=100)


# ─── Réponses (sorties) ───────────────────────────────────────────────────────

class UsageEntryResponse(BaseModel):
    """Usage détaillé pour une application."""
    package_name: str
    app_name: str
    duration_seconds: int
    usage_date: date

    model_config = {"from_attributes": True}


class DailyUsageResponse(BaseModel):
    """Usage total pour une journée donnée, détaillé par application."""
    date: date
    total_seconds: int
    apps: List[UsageEntryResponse]

    def calculate_total(cls, apps: List[UsageEntryResponse]) -> int:
        return sum(app.duration_seconds for app in apps)


class WeeklyUsageItem(BaseModel):
    """Résumé de l'usage pour un jour (utilisé dans le graphe hebdomadaire)."""
    date: date
    total_seconds: int


class WeeklyUsageResponse(BaseModel):
    """Usage des 7 derniers jours, total par jour."""
    days: List[WeeklyUsageItem]
    total_seconds: int

    @classmethod
    def from_days(cls, days: List[WeeklyUsageItem]) -> "WeeklyUsageResponse":
        return cls(days=days, total_seconds=sum(d.total_seconds for d in days))


class UsageSummaryResponse(BaseModel):
    """Résumé de l'usage aujourd'hui."""
    today_seconds: int
    today_limit_seconds: Optional[int] = None  # Si une règle SCREEN_LIMIT existe
    percentage_used: float  # 0.0 à 100.0+ (peut dépasser 100% si limite dépassée)
    top_apps: List[UsageEntryResponse]  # Top 3 apps les plus utilisées
