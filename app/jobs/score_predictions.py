"""Tâche de calcul des points, lancée après chaque mise à jour des scores."""
from datetime import datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Match, Prediction
from app.models.match import MatchStatus
from app.services.scoring import ScoringRules, score_prediction

# Les matchs récents sont recalculés à chaque passage : si l'API corrige
# un score final (import quotidien de J-3), les points suivent.
RESCORE_WINDOW = timedelta(days=3)


def apply_result(prediction: Prediction, match: Match, rules: ScoringRules,
                 now: datetime) -> None:
    """Met à jour les points d'un pronostic selon l'état de son match."""
    if match.status == MatchStatus.CANCELLED or match.home_score is None:
        # Match annulé : pronostic annulé, 0 point et non compté
        prediction.points, prediction.is_exact, prediction.is_winner = None, False, False
    else:
        result = score_prediction(prediction.home_score, prediction.away_score,
                                  match.home_score, match.away_score, rules)
        prediction.points = result.points
        prediction.is_exact, prediction.is_winner = result.is_exact, result.is_winner
    prediction.scored_at = now


def score_match(db: Session, match: Match, rules: ScoringRules, now: datetime) -> int:
    """Recalcule tous les pronostics d'un match (servira aussi à la correction admin)."""
    predictions = db.scalars(select(Prediction).where(Prediction.match_id == match.id)).all()
    for prediction in predictions:
        apply_result(prediction, match, rules, now)
    db.commit()
    return len(predictions)


def score_finished_matches(db: Session, rules: ScoringRules, now: datetime) -> int:
    """Calcule les pronostics des matchs terminés ou annulés pas encore traités,
    et recalcule ceux des matchs récents. Renvoie le nombre de pronostics traités."""
    rows = db.execute(
        select(Prediction, Match)
        .join(Match, Prediction.match_id == Match.id)
        .where(
            Match.status.in_([MatchStatus.FINISHED, MatchStatus.CANCELLED]),
            or_(Prediction.scored_at.is_(None), Match.kickoff_at >= now - RESCORE_WINDOW),
        )
    ).all()
    for prediction, match in rows:
        apply_result(prediction, match, rules, now)
    db.commit()
    return len(rows)
