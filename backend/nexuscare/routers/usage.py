"""
Router Usage — endpoints pour le suivi du temps d'écran.
Préfixe : /api/v1/children/{child_id}/usage
Auth : parent pour lecture, device (enfant) pour écriture
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from nexuscare.core.database import get_db
from nexuscare.core.dependencies import get_current_parent, get_current_child
from nexuscare.models.parent import Parent
from nexuscare.models.child import Child
from nexuscare.schemas.usage import (
    DailyUsageResponse,
    UsageReportRequest,
    WeeklyUsageResponse,
    UsageSummaryResponse,
)
from nexuscare.services import usage_service

router = APIRouter(prefix="/children", tags=["Usage — Temps d'écran"])


@router.post(
    "/{child_id}/usage",
    status_code=status.HTTP_200_OK,
    summary="Envoyer un rapport d'usage (APK Enfant)",
    description="Endpoint appelé par l'APK Enfant toutes les 5 minutes pour rapporter le temps d'écran.",
)
def report_usage(
    child_id: int,
    data: UsageReportRequest,
    db: Session = Depends(get_db),
    current_child: Child = Depends(get_current_child),
) -> dict:
    """
    Enregistre un rapport d'usage envoyé par l'APK Enfant.
    - Auth : token device (enfant uniquement)
    - UPSERT : si entrée existe, additionne la durée
    - Vérifie que child_id correspond au token device
    """
    # Sécurité : l'enfant ne peut rapporter que son propre usage
    if current_child.id != child_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez rapporter que votre propre usage.",
        )
    
    return usage_service.report_usage(child_id, data, db)


@router.get(
    "/{child_id}/usage/today",
    response_model=DailyUsageResponse,
    summary="Usage du jour courant",
    description="Récupère l'usage du jour pour un enfant, groupé par application.",
)
def get_today(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
) -> DailyUsageResponse:
    """
    Récupère l'usage du jour courant pour un enfant.
    - Auth : token parent requis
    - Vérifie que le parent est propriétaire de l'enfant
    """
    # Vérifie que le parent est propriétaire de l'enfant
    child = db.get(Child, child_id)
    if child is None or child.parent_id != current_parent.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enfant non trouvé ou non autorisé.",
        )
    
    return usage_service.get_today_usage(child_id, db)


@router.get(
    "/{child_id}/usage/weekly",
    response_model=WeeklyUsageResponse,
    summary="Usage des 7 derniers jours",
    description="Récupère l'usage total par jour pour les 7 derniers jours.",
)
def get_weekly(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
) -> WeeklyUsageResponse:
    """
    Récupère l'usage des 7 derniers jours, total par jour.
    - Auth : token parent requis
    - Vérifie que le parent est propriétaire de l'enfant
    """
    # Vérifie que le parent est propriétaire de l'enfant
    child = db.get(Child, child_id)
    if child is None or child.parent_id != current_parent.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enfant non trouvé ou non autorisé.",
        )
    
    return usage_service.get_weekly_usage(child_id, db)


@router.get(
    "/{child_id}/usage/daily",
    response_model=DailyUsageResponse,
    summary="Usage d'un jour précis",
    description="Récupère l'usage détaillé pour une date donnée.",
)
def get_daily(
    child_id: int,
    date: Optional[date] = Query(default=None, description="Date au format YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
) -> DailyUsageResponse:
    """
    Récupère l'usage d'un jour précis, détaillé par application.
    - Auth : token parent requis
    - Si date non fournie, utilise aujourd'hui
    - Vérifie que le parent est propriétaire de l'enfant
    """
    from datetime import datetime, timezone
    
    target_date = date or datetime.now(timezone.utc).date()
    
    # Vérifie que le parent est propriétaire de l'enfant
    child = db.get(Child, child_id)
    if child is None or child.parent_id != current_parent.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enfant non trouvé ou non autorisé.",
        )
    
    return usage_service.get_daily_usage(child_id, target_date, db)


@router.get(
    "/{child_id}/usage/summary",
    response_model=UsageSummaryResponse,
    summary="Résumé de l'usage aujourd'hui",
    description="Résumé avec limite, pourcentage et top 3 apps.",
)
def get_summary(
    child_id: int,
    db: Session = Depends(get_db),
    current_parent: Parent = Depends(get_current_parent),
) -> UsageSummaryResponse:
    """
    Résumé de l'usage aujourd'hui avec limite et top apps.
    - Auth : token parent requis
    - Vérifie que le parent est propriétaire de l'enfant
    """
    # Vérifie que le parent est propriétaire de l'enfant
    child = db.get(Child, child_id)
    if child is None or child.parent_id != current_parent.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enfant non trouvé ou non autorisé.",
        )
    
    return usage_service.get_usage_summary(child_id, db)
