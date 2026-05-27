"""
Router Usage — Suivi du temps d'écran des enfants.
Préfixe : /api/v1/children/{child_id}/usage
Endpoints appelés par l'APK Enfant (POST) et le dashboard Parent (GET).
"""
from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Annotated

from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent, get_current_child
from nexuscare.models.parent import Parent
from nexuscare.models.child import Child
from nexuscare.schemas.usage import (
    UsageReportRequest,
    DailyUsageResponse,
    WeeklyUsageResponse,
    MessageResponse,
)
from nexuscare.services import usage_service

router = APIRouter(prefix="/children", tags=["Usage"])


@router.post(
    "/{child_id}/usage",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Envoyer un rapport d'utilisation (APK Enfant)",
)
def report_usage(
    child_id: int,
    data: UsageReportRequest,
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
) -> MessageResponse:
    """
    Endpoint appelé par l'APK Enfant toutes les 5 minutes.
    Envoie une liste d'applications utilisées avec leur durée.
    UPSERT : si une entrée existe pour (child_id, package_name, usage_date),
    la durée est additionnée (pas de remplacement).
    
    Auth : token enfant requis (device_id dans le JWT).
    """
    # Vérifie que le token enfant correspond bien au child_id de l'URL
    if current_child.id != child_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token enfant non correspondant à cet ID.",
        )
    
    result = usage_service.report_usage(child_id, data, db)
    return MessageResponse(message=result["message"])


@router.get(
    "/{child_id}/usage/today",
    response_model=DailyUsageResponse,
    summary="Usage du jour (Parent)",
)
def get_today(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> DailyUsageResponse:
    """
    Récupère l'usage du jour courant pour un enfant, groupé par application.
    Utilisé par le dashboard parent pour afficher le temps d'écran du jour.
    """
    return usage_service.get_today_usage(child_id, current_parent, db)


@router.get(
    "/{child_id}/usage/weekly",
    response_model=WeeklyUsageResponse,
    summary="Usage hebdomadaire (7 jours)",
)
def get_weekly(
    child_id: int,
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> WeeklyUsageResponse:
    """
    Récupère l'usage des 7 derniers jours, total par jour.
    Utilisé pour le graphe à barres du dashboard parent.
    Retourne toujours 7 jours (même si certains ont 0 seconde d'usage).
    """
    return usage_service.get_weekly_usage(child_id, current_parent, db)


@router.get(
    "/{child_id}/usage/daily",
    response_model=DailyUsageResponse,
    summary="Usage d'un jour précis",
)
def get_daily(
    child_id: int,
    date_param: Annotated[date, Query(alias="date")],
    current_parent: Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
) -> DailyUsageResponse:
    """
    Récupère l'usage détaillé d'un jour précis.
    Paramètre : ?date=YYYY-MM-DD
    """
    return usage_service.get_daily_usage(child_id, date_param, current_parent, db)
