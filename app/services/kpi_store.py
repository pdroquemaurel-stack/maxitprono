"""Lectures en base pour les KPIs ; le calcul semaine par semaine est dans kpis.py.

Les joueurs fictifs de la démo (pseudos « demo_… ») sont comptés à part.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ApiCallLog, League, Prediction, User
from app.services.kpis import WeekRow, last_mondays, weekly_rows
from app.services.ranking import week_bounds

DEMO_PREFIX = "demo_"
API_WINDOW = timedelta(days=7)


@dataclass(frozen=True)
class Totals:
    players: int
    demo_players: int
    leagues: int
    predictions: int
    api_calls: int  # sur les 7 derniers jours
    api_errors: int
    last_api_error: ApiCallLog | None


def _real_players():
    return User.nickname_key.not_like(f"{DEMO_PREFIX}%")


def _count(db: Session, query) -> int:
    return db.scalar(select(func.count()).select_from(query.subquery()))


def totals(db: Session, now: datetime) -> Totals:
    since = now - API_WINDOW
    real_ids = select(User.id).where(_real_players())
    return Totals(
        players=_count(db, select(User.id).where(_real_players())),
        demo_players=_count(db, select(User.id).where(User.nickname_key.like(f"{DEMO_PREFIX}%"))),
        leagues=_count(db, select(League.id)),
        predictions=_count(db, select(Prediction.id).where(Prediction.user_id.in_(real_ids))),
        api_calls=_count(db, select(ApiCallLog.id).where(ApiCallLog.called_at >= since)),
        api_errors=_count(db, select(ApiCallLog.id).where(ApiCallLog.called_at >= since,
                                                          ApiCallLog.error != "")),
        last_api_error=db.scalar(select(ApiCallLog).where(ApiCallLog.error != "")
                                 .order_by(ApiCallLog.called_at.desc()).limit(1)),
    )


def weekly(db: Session, today: date) -> list[WeekRow]:
    """Tableau des 8 dernières semaines (seules ces semaines sont lues en base)."""
    mondays = last_mondays(today)
    since = week_bounds(mondays[-1])[0]
    signups = list(db.scalars(select(User.created_at)
                              .where(_real_players(), User.created_at >= since)))
    events = [tuple(row) for row in db.execute(
        select(Prediction.user_id, Prediction.created_at, Prediction.updated_at)
        .join(User, User.id == Prediction.user_id)
        .where(_real_players(), Prediction.updated_at >= since))]
    leagues = list(db.scalars(select(League.created_at).where(League.created_at >= since)))
    return weekly_rows(mondays, signups, events, leagues)
