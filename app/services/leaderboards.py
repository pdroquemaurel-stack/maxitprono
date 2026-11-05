"""Lecture des classements en base : une seule requête agrégée par classement.

Seuls les pronostics calculés et comptés (points non vides) entrent en compte :
un joueur sans aucun pronostic calculé n'apparaît pas.
"""
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import LeagueMember, Match, Prediction, User
from app.services.ranking import PlayerScore, rank_players


def leaderboard(db: Session, country_code: str | None = None, competition_id: int | None = None,
                period: tuple[datetime, datetime] | None = None,
                league_id: int | None = None) -> list[PlayerScore]:
    """Classement complet, filtré par pays du joueur, compétition, semaine ou ligue.

    Pour une ligue : ses membres seulement, et pour chacun les matchs commencés
    après son arrivée dans la ligue.
    """
    query = (
        select(User.id, User.nickname, User.country_code, User.created_at,
               func.sum(Prediction.points),
               func.sum(case((Prediction.is_exact, 1), else_=0)),
               func.sum(case((Prediction.is_winner, 1), else_=0)))
        .join(Prediction, Prediction.user_id == User.id)
        .join(Match, Prediction.match_id == Match.id)
        .where(Prediction.points.is_not(None))
        .group_by(User.id)
    )
    if country_code:
        query = query.where(User.country_code == country_code)
    if competition_id:
        query = query.where(Match.competition_id == competition_id)
    if period:
        query = query.where(Match.kickoff_at >= period[0], Match.kickoff_at < period[1])
    if league_id:
        query = (query.join(LeagueMember, LeagueMember.user_id == User.id)
                 .where(LeagueMember.league_id == league_id,
                        Match.kickoff_at >= LeagueMember.joined_at))

    players = [PlayerScore(user_id, nickname, country, created_at, points, exacts, winners)
               for user_id, nickname, country, created_at, points, exacts, winners
               in db.execute(query)]
    return rank_players(players)
