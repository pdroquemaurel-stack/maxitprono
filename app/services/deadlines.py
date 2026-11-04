"""Clôture des pronostics : 10 minutes avant le coup d'envoi.

Fonctions pures : la date courante est passée en paramètre.
"""
from datetime import datetime, timedelta

from app.models.match import MatchStatus

CLOSING_DELAY = timedelta(minutes=10)

# Un match reporté reste pronostiquable : il rouvre quand l'API donne sa nouvelle date
OPEN_STATUSES = (MatchStatus.SCHEDULED, MatchStatus.POSTPONED)


def prediction_deadline(kickoff_at: datetime) -> datetime:
    return kickoff_at - CLOSING_DELAY


def is_prediction_open(status: str, kickoff_at: datetime, now: datetime) -> bool:
    """Vrai si on peut encore saisir ou modifier un pronostic sur ce match."""
    return status in OPEN_STATUSES and now < prediction_deadline(kickoff_at)
