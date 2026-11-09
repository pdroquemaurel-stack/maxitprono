"""Historique des rangs au classement général, une photo par journée de matchs.

Sert au badge Remontada (places gagnées en une journée) sans relire tous les pronostics.
"""
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Match, Prediction, RankSnapshot
from app.services.leaderboards import leaderboard

EPOCH = datetime(2000, 1, 1, tzinfo=UTC)


def refresh_rank_snapshots(db: Session, since: date | None = None) -> int:
    """Refait les photos des journées à partir de `since` (toutes si None).

    Table vide (premier passage) : tout est reconstruit. Renvoie le nombre de journées.
    """
    if since is not None and db.scalar(select(RankSnapshot.id).limit(1)) is None:
        since = None
    kickoffs = db.scalars(select(Match.kickoff_at).distinct()
                          .join(Prediction, Prediction.match_id == Match.id)
                          .where(Prediction.points.is_not(None)))
    days = sorted({kickoff.date() for kickoff in kickoffs if since is None or kickoff.date() >= since})

    old = delete(RankSnapshot)
    db.execute(old if since is None else old.where(RankSnapshot.day >= since))
    for day in days:
        end_of_day = datetime.combine(day + timedelta(days=1), time.min, tzinfo=UTC)
        db.add_all(RankSnapshot(day=day, user_id=player.user_id, rank=player.rank,
                                points=player.points)
                   for player in leaderboard(db, period=(EPOCH, end_of_day)))
    db.commit()
    return len(days)


def player_ranks(db: Session, user_id: int) -> list[tuple[date, int]]:
    """(jour, rang) du joueur, du plus ancien au plus récent."""
    query = (select(RankSnapshot.day, RankSnapshot.rank)
             .where(RankSnapshot.user_id == user_id).order_by(RankSnapshot.day))
    return [(day, rank) for day, rank in db.execute(query)]
