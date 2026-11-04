"""Enregistrement d'un pronostic, avec contrôle de la clôture côté serveur."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Match, Prediction
from app.services.deadlines import is_prediction_open

MAX_SCORE = 20


def parse_score(value: str) -> int | None:
    """Score saisi par le joueur : entier de 0 à 20, sinon None."""
    value = value.strip()
    if not value.isdigit() or not value.isascii():
        return None
    score = int(value)
    return score if score <= MAX_SCORE else None


def prediction_error(match: Match | None, home: int | None, away: int | None,
                     now: datetime) -> str | None:
    """Clé de traduction de l'erreur, ou None si le pronostic est acceptable (fonction pure)."""
    if match is None:
        return "error_match_not_found"
    if not is_prediction_open(match.status, match.kickoff_at, now):
        return "error_prediction_closed"
    if home is None or away is None:
        return "error_score_format"
    return None


def save_prediction(db: Session, user_id: int, match_id: int, home_raw: str, away_raw: str,
                    now: datetime) -> str | None:
    """Crée ou met à jour le pronostic. Renvoie une clé d'erreur, ou None si enregistré."""
    match = db.get(Match, match_id)
    home, away = parse_score(home_raw), parse_score(away_raw)
    error = prediction_error(match, home, away, now)
    if error:
        return error

    try:
        _upsert(db, user_id, match_id, home, away, now)
    except IntegrityError:
        # Double envoi simultané (double appui sur mobile) : l'autre requête a créé
        # la ligne entre-temps, on refait l'opération qui devient une mise à jour.
        db.rollback()
        _upsert(db, user_id, match_id, home, away, now)
    return None


def _upsert(db: Session, user_id: int, match_id: int, home: int, away: int,
            now: datetime) -> None:
    prediction = db.scalar(select(Prediction).where(Prediction.user_id == user_id,
                                                    Prediction.match_id == match_id))
    if prediction is None:
        prediction = Prediction(user_id=user_id, match_id=match_id, created_at=now)
        db.add(prediction)
    prediction.home_score, prediction.away_score, prediction.updated_at = home, away, now
    db.commit()
