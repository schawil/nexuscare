"""
Service Usage — logique métier pour le suivi du temps d'écran.
Gère l'enregistrement (UPSERT) des usages et les requêtes de rapports.
"""
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException, status

from nexuscare.models.app_usage import AppUsage
from nexuscare.models.child import Child
from nexuscare.models.parent import Parent
from nexuscare.schemas.usage import (
    UsageReportRequest,
    DailyUsageResponse,
    WeeklyUsageResponse,
)


def _get_child_or_404(child_id: int, parent: Parent | None, db: Session) -> Child:
    """Récupère un enfant ou lève une 404 si inexistant ou non accessible."""
    child = db.get(Child, child_id)
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    
    # Si parent fourni, vérifie l'accès
    if parent is not None and child.parent_id != parent.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enfant introuvable.")
    
    return child


def report_usage(child_id: int, data: UsageReportRequest, db: Session) -> dict:
    """
    Enregistre un rapport d'utilisation envoyé par l'APK Enfant.
    UPSERT : si une entrée existe pour (child_id, package_name, usage_date),
    on additionne la durée au lieu de remplacer.
    """
    child = _get_child_or_404(child_id, None, db)
    
    entries_processed = 0
    for entry in data.usages:
        # Vérifie si une entrée existe déjà pour ce jour + package
        existing = db.query(AppUsage).filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.package_name == entry.package_name,
                AppUsage.usage_date == entry.usage_date,
            )
        ).first()
        
        if existing:
            # UPSERT : additionne la durée
            existing.duration_seconds += entry.duration_seconds
            existing.app_name = entry.app_name  # Met à jour le nom si changé
            existing.updated_at = datetime.utcnow()
        else:
            # CREATE : nouvelle entrée
            new_usage = AppUsage(
                child_id=child_id,
                package_name=entry.package_name,
                app_name=entry.app_name,
                duration_seconds=entry.duration_seconds,
                usage_date=entry.usage_date,
            )
            db.add(new_usage)
        
        entries_processed += 1
    
    db.commit()
    
    return {"message": f"{entries_processed} entrées enregistrées.", "entries_count": entries_processed}


def get_today_usage(child_id: int, parent: Parent, db: Session) -> DailyUsageResponse:
    """Récupère l'usage du jour courant pour un enfant, groupé par app."""
    _get_child_or_404(child_id, parent, db)
    
    today = date.today()
    
    # Récupère toutes les entrées du jour
    entries = (
        db.query(AppUsage)
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == today,
            )
        )
        .all()
    )
    
    # Groupe par package_name
    grouped: dict[str, dict] = {}
    for entry in entries:
        if entry.package_name not in grouped:
            grouped[entry.package_name] = {
                "package_name": entry.package_name,
                "app_name": entry.app_name,
                "total_seconds": 0,
            }
        grouped[entry.package_name]["total_seconds"] += entry.duration_seconds
    
    # Convertit en liste triée par durée décroissante
    entries_list = sorted(grouped.values(), key=lambda x: x["total_seconds"], reverse=True)
    
    return DailyUsageResponse.from_entries(today, entries_list)


def get_weekly_usage(child_id: int, parent: Parent, db: Session) -> WeeklyUsageResponse:
    """Récupère l'usage des 7 derniers jours, total par jour."""
    _get_child_or_404(child_id, parent, db)
    
    today = date.today()
    start_date = today - timedelta(days=6)  # 7 jours incluant aujourd'hui
    
    # Requête SQL pour grouper par date et sommer les durées
    results = (
        db.query(
            AppUsage.usage_date,
            func.sum(AppUsage.duration_seconds).label("total_seconds"),
        )
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date >= start_date,
                AppUsage.usage_date <= today,
            )
        )
        .group_by(AppUsage.usage_date)
        .order_by(AppUsage.usage_date.asc())
        .all()
    )
    
    # Construit la réponse avec tous les jours (même ceux sans usage = 0)
    days_list: list[dict] = []
    result_dict = {r.usage_date: r.total_seconds for r in results}
    
    current = start_date
    while current <= today:
        days_list.append({
            "date": current,
            "total_seconds": result_dict.get(current, 0),
        })
        current += timedelta(days=1)
    
    return WeeklyUsageResponse.from_days(days_list)


def get_daily_usage(child_id: int, target_date: date, parent: Parent, db: Session) -> DailyUsageResponse:
    """Récupère l'usage détaillé d'un jour précis."""
    _get_child_or_404(child_id, parent, db)
    
    # Récupère toutes les entrées du jour
    entries = (
        db.query(AppUsage)
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == target_date,
            )
        )
        .all()
    )
    
    # Groupe par package_name
    grouped: dict[str, dict] = {}
    for entry in entries:
        if entry.package_name not in grouped:
            grouped[entry.package_name] = {
                "package_name": entry.package_name,
                "app_name": entry.app_name,
                "total_seconds": 0,
            }
        grouped[entry.package_name]["total_seconds"] += entry.duration_seconds
    
    # Convertit en liste triée par durée décroissante
    entries_list = sorted(grouped.values(), key=lambda x: x["total_seconds"], reverse=True)
    
    return DailyUsageResponse.from_entries(target_date, entries_list)


def cleanup_old_usage(db: Session, days_to_keep: int = 30) -> int:
    """
    Supprime les entrées app_usage de plus de `days_to_keep` jours.
    Retourne le nombre d'entrées supprimées.
    À appeler au démarrage du serveur ou via job planifié.
    """
    cutoff_date = date.today() - timedelta(days=days_to_keep)
    
    deleted_count = (
        db.query(AppUsage)
        .filter(AppUsage.usage_date < cutoff_date)
        .delete(synchronize_session=False)
    )
    
    db.commit()
    return deleted_count
