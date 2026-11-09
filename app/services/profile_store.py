"""Lectures en base pour la page Profil ; les calculs sont dans profile_stats.py."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LeagueMember, Match, Prediction, User
from app.models.match import MatchStatus
from app.services.profile_stats import DayScore, PlayedPick
from app.services.ranking import PlayerScore


def played_picks(db: Session, user_id: int) -> list[PlayedPick]:
    """Tous les pronos du joueur sur des matchs terminés (score final connu)."""
    query = (select(Prediction, Match)
             .join(Match, Prediction.match_id == Match.id)
             .where(Prediction.user_id == user_id, Match.status == MatchStatus.FINISHED,
                    Match.home_score.is_not(None), Match.away_score.is_not(None)))
    return [PlayedPick(pred_home=prediction.home_score, pred_away=prediction.away_score,
                       real_home=match.home_score, real_away=match.away_score,
                       kickoff_at=match.kickoff_at, competition=match.competition.name,
                       competition_id=match.competition_id, points=prediction.points or 0,
                       matchday=match.matchday)
            for prediction, match in db.execute(query)]


def daily_scores(db: Session) -> list[DayScore]:
    """Points de chaque joueur par journée, pour le classement général.

    Lit tous les pronostics calculés : suffisant pour le POC (voir docs/STATUS.md).
    """
    query = (select(User.id, User.nickname, User.country_code, User.created_at,
                    Match.kickoff_at, Prediction.points, Prediction.is_exact, Prediction.is_winner)
             .join(Prediction, Prediction.user_id == User.id)
             .join(Match, Prediction.match_id == Match.id)
             .where(Prediction.points.is_not(None)))
    return [DayScore(PlayerScore(user_id, nickname, country, created_at, points,
                                 int(exact), int(winner)), kickoff_at.date())
            for user_id, nickname, country, created_at, kickoff_at, points, exact, winner
            in db.execute(query)]


def invited_friends(db: Session, user_id: int) -> int:
    """Joueurs entrés dans une ligue grâce à mon lien d'invitation (et toujours membres)."""
    return db.scalar(select(func.count()).select_from(LeagueMember)
                     .where(LeagueMember.invited_by_id == user_id))


def nickname_taken(db: Session, key: str, user_id: int) -> bool:
    """Pseudo déjà pris par un autre joueur."""
    return db.scalar(select(User.id).where(User.nickname_key == key, User.id != user_id)) is not None
