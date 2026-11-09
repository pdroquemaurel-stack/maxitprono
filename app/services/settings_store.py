"""Lecture et écriture des réglages du jeu (table game_settings, une seule ligne)."""
from datetime import datetime

from sqlalchemy.orm import Session

from app.jobs.score_predictions import rescore_all
from app.models import GameSettings
from app.services.game_settings import Settings
from app.services.scoring import ScoringRules

SETTINGS_ID = 1


def get_settings(db: Session) -> Settings:
    """Réglages en base, ou valeurs par défaut tant que l'admin n'a rien enregistré."""
    row = db.get(GameSettings, SETTINGS_ID)
    if row is None:
        return Settings()
    return Settings(row.winner_points, row.exact_bonus, row.league_max_members,
                    row.prediction_days_ahead)


def current_rules(db: Session) -> ScoringRules:
    return get_settings(db).rules


def league_max_members(db: Session) -> int:
    return get_settings(db).league_max_members


def prediction_days_ahead(db: Session) -> int:
    return get_settings(db).prediction_days_ahead


def save_settings(db: Session, settings: Settings, now: datetime) -> int:
    """Enregistre les réglages ; si le barème change, recalcule tous les pronostics.

    Renvoie le nombre de pronostics recalculés (0 si le barème n'a pas changé).
    """
    changed = get_settings(db).rules != settings.rules
    row = db.get(GameSettings, SETTINGS_ID) or GameSettings(id=SETTINGS_ID)
    row.winner_points, row.exact_bonus = settings.winner_points, settings.exact_bonus
    row.league_max_members = settings.league_max_members
    row.prediction_days_ahead, row.updated_at = settings.prediction_days_ahead, now
    db.add(row)
    db.commit()
    return rescore_all(db, settings.rules, now) if changed else 0
