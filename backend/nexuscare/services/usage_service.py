"""
Service Usage — logique métier pour le suivi du temps d'écran.
Pattern Service Layer : les routers délèguent ici, les tests unitaires testent ici.
"""
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from nexuscare.models.app_usage import AppUsage
from nexuscare.models.child import Child
from nexuscare.models.rule import Rule
from nexuscare.schemas.usage import (
    DailyUsageResponse,
    UsageEntry,
    UsageEntryResponse,
    UsageReportRequest,
    WeeklyUsageItem,
    WeeklyUsageResponse,
    UsageSummaryResponse,
)


def report_usage(child_id: int, data: UsageReportRequest, db: Session) -> dict:
    """
    Enregistre un rapport d'usage envoyé par l'APK Enfant.
    UPSERT : si une entrée existe pour (child_id, package_name, usage_date),
    on additionne la durée (ne remplace pas).
    
    Retourne un résumé de l'opération.
    """
    entries_processed = 0
    entries_updated = 0
    entries_created = 0
    
    for entry in data.usages:
        existing = db.query(AppUsage).filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.package_name == entry.package_name,
                AppUsage.usage_date == entry.usage_date,
            )
        ).first()
        
        if existing:
            # UPSERT : on additionne la durée
            existing.duration_seconds += entry.duration_seconds
            existing.app_name = entry.app_name  # Met à jour le nom si changé
            entries_updated += 1
        else:
            # Création nouvelle entrée
            db_entry = AppUsage(
                child_id=child_id,
                package_name=entry.package_name,
                app_name=entry.app_name,
                duration_seconds=entry.duration_seconds,
                usage_date=entry.usage_date,
            )
            db.add(db_entry)
            entries_created += 1
        
        entries_processed += 1
    
    db.commit()
    
    return {
        "entries_processed": entries_processed,
        "entries_updated": entries_updated,
        "entries_created": entries_created,
    }


def get_today_usage(child_id: int, db: Session) -> DailyUsageResponse:
    """
    Récupère l'usage du jour courant pour un enfant, groupé par application.
    Utilisé par le dashboard parent.
    """
    today = datetime.now(timezone.utc).date()
    
    apps = (
        db.query(AppUsage)
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == today,
            )
        )
        .order_by(AppUsage.duration_seconds.desc())
        .all()
    )
    
    total_seconds = sum(app.duration_seconds for app in apps)
    
    # Vérifie s'il y a une règle SCREEN_LIMIT active
    screen_limit_rule = db.query(Rule).filter(
        and_(
            Rule.child_id == child_id,
            Rule.rule_type == "SCREEN_LIMIT",
            Rule.is_active.is_(True),
        )
    ).first()
    
    limit_seconds = None
    if screen_limit_rule and screen_limit_rule.config:
        limit_seconds = screen_limit_rule.config.get("daily_limit_seconds")
    
    percentage_used = 0.0
    if limit_seconds and limit_seconds > 0:
        percentage_used = (total_seconds / limit_seconds) * 100
    
    return DailyUsageResponse(
        date=today,
        total_seconds=total_seconds,
        apps=[UsageEntryResponse.model_validate(app) for app in apps],
    )


def get_weekly_usage(child_id: int, db: Session) -> WeeklyUsageResponse:
    """
    Récupère l'usage des 7 derniers jours, total par jour.
    Utilisé pour le graphe barres du dashboard parent.
    """
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)
    
    # Requête SQL pour grouper par date et sommer les durées
    results = (
        db.query(
            AppUsage.usage_date,
            func.sum(AppUsage.duration_seconds).label("total_seconds"),
        )
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date >= seven_days_ago,
                AppUsage.usage_date <= today,
            )
        )
        .group_by(AppUsage.usage_date)
        .order_by(AppUsage.usage_date.asc())
        .all()
    )
    
    # Construit la réponse avec tous les jours (même ceux sans usage = 0)
    days_dict = {row.usage_date: row.total_seconds for row in results}
    
    days_list: List[WeeklyUsageItem] = []
    current_date = seven_days_ago
    while current_date <= today:
        days_list.append(
            WeeklyUsageItem(
                date=current_date,
                total_seconds=days_dict.get(current_date, 0),
            )
        )
        current_date += timedelta(days=1)
    
    return WeeklyUsageResponse.from_days(days_list)


def get_daily_usage(child_id: int, target_date: date, db: Session) -> DailyUsageResponse:
    """
    Récupère l'usage d'un jour précis, détaillé par application.
    """
    apps = (
        db.query(AppUsage)
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == target_date,
            )
        )
        .order_by(AppUsage.duration_seconds.desc())
        .all()
    )
    
    total_seconds = sum(app.duration_seconds for app in apps)
    
    return DailyUsageResponse(
        date=target_date,
        total_seconds=total_seconds,
        apps=[UsageEntryResponse.model_validate(app) for app in apps],
    )


def get_usage_summary(child_id: int, db: Session) -> UsageSummaryResponse:
    """
    Résumé de l'usage aujourd'hui avec limite et top apps.
    Utilisé pour les cartes du dashboard parent.
    """
    today = datetime.now(timezone.utc).date()
    
    # Récupère toutes les apps du jour
    apps = (
        db.query(AppUsage)
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == today,
            )
        )
        .order_by(AppUsage.duration_seconds.desc())
        .limit(3)  # Top 3 seulement
        .all()
    )
    
    # Calcule le total (toutes les apps, pas juste top 3)
    total_result = (
        db.query(func.sum(AppUsage.duration_seconds))
        .filter(
            and_(
                AppUsage.child_id == child_id,
                AppUsage.usage_date == today,
            )
        )
        .scalar()
    ) or 0
    
    # Vérifie la limite SCREEN_LIMIT
    screen_limit_rule = db.query(Rule).filter(
        and_(
            Rule.child_id == child_id,
            Rule.rule_type == "SCREEN_LIMIT",
            Rule.is_active.is_(True),
        )
    ).first()
    
    limit_seconds = None
    percentage_used = 0.0
    if screen_limit_rule and screen_limit_rule.config:
        limit_seconds = screen_limit_rule.config.get("daily_limit_seconds")
        if limit_seconds and limit_seconds > 0:
            percentage_used = (total_result / limit_seconds) * 100
    
    return UsageSummaryResponse(
        today_seconds=total_result,
        today_limit_seconds=limit_seconds,
        percentage_used=percentage_used,
        top_apps=[UsageEntryResponse.model_validate(app) for app in apps],
    )


def cleanup_old_usage(db: Session, days_to_keep: int = 30) -> int:
    """
    Supprime les entrées app_usage de plus de N jours.
    À appeler au démarrage ou via une tâche planifiée.
    
    Retourne le nombre d'entrées supprimées.
    """
    cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=days_to_keep)
    
    deleted = (
        db.query(AppUsage)
        .filter(AppUsage.usage_date < cutoff_date)
        .delete(synchronize_session=False)
    )
    
    db.commit()
    return deleted
