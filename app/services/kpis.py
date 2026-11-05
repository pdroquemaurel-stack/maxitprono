"""KPIs du back-office (SPEC §9), semaine par semaine. Fonctions pures : aucune base.

Semaines du lundi au dimanche, en UTC, comme le classement de la semaine.
« Joueur actif » : a fait ou modifié au moins un pronostic dans la semaine.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.services.ranking import week_start

WEEKS_SHOWN = 8


@dataclass(frozen=True)
class WeekRow:
    monday: date
    new_players: int
    active_players: int
    predictions: int  # pronostics faits dans la semaine
    leagues: int  # ligues créées

    @property
    def predictions_per_active(self) -> float:
        """Moyenne de pronostics faits par joueur actif, à 0,1 près."""
        return round(self.predictions / self.active_players, 1) if self.active_players else 0.0


def last_mondays(today: date, count: int = WEEKS_SHOWN) -> list[date]:
    """Lundis des `count` dernières semaines, la semaine en cours d'abord."""
    current = week_start(today)
    return [current - timedelta(weeks=i) for i in range(count)]


def weekly_rows(mondays: list[date], signups: list[datetime],
                prediction_events: list[tuple[int, datetime, datetime]],
                league_creations: list[datetime]) -> list[WeekRow]:
    """Une ligne par semaine.

    `prediction_events` : (user_id, créé le, modifié le) de chaque pronostic.
    """
    def monday_of(moment: datetime) -> date:
        return week_start(moment.date())

    rows = []
    for monday in mondays:
        active = {user_id for user_id, created, updated in prediction_events
                  if monday in (monday_of(created), monday_of(updated))}
        made = sum(1 for _, created, _ in prediction_events if monday_of(created) == monday)
        rows.append(WeekRow(
            monday=monday,
            new_players=sum(1 for moment in signups if monday_of(moment) == monday),
            active_players=len(active),
            predictions=made,
            leagues=sum(1 for moment in league_creations if monday_of(moment) == monday),
        ))
    return rows
