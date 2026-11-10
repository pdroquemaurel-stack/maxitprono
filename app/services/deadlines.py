"""Clôture des pronostics : 10 minutes avant le coup d'envoi.

Fonctions pures : la date courante est passée en paramètre.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo

from app.models.match import MatchStatus

CLOSING_DELAY = timedelta(minutes=10)

# Un match reporté reste pronostiquable : il rouvre quand l'API donne sa nouvelle date
OPEN_STATUSES = (MatchStatus.SCHEDULED, MatchStatus.POSTPONED)


def prediction_deadline(kickoff_at: datetime) -> datetime:
    return kickoff_at - CLOSING_DELAY


def is_prediction_open(status: str, kickoff_at: datetime, now: datetime) -> bool:
    """Vrai si on peut encore saisir ou modifier un pronostic sur ce match."""
    return status in OPEN_STATUSES and now < prediction_deadline(kickoff_at)


# --- Délai avant clôture, pour l'affichage (« Ferme dans 1 h 42 », « Ferme demain »...) ---

SOON_LIMIT = timedelta(hours=6)  # en dessous, on affiche toujours la durée restante


@dataclass(frozen=True)
class ClosingInfo:
    kind: str  # "soon" (durée restante), "tomorrow" ou "later" (jour de la semaine)
    hours: int = 0
    minutes: int = 0
    day: date | None = None  # jour local de la clôture, pour "later"


def closing_info(kickoff_at: datetime, now: datetime, tz: tzinfo) -> ClosingInfo:
    """Quand ferme le pronostic, vu depuis le fuseau du joueur."""
    deadline = prediction_deadline(kickoff_at)
    remaining = max(deadline - now, timedelta(0))
    deadline_day = deadline.astimezone(tz).date()
    today = now.astimezone(tz).date()
    if deadline_day == today or remaining < SOON_LIMIT:
        total_minutes = max(1, int(remaining.total_seconds() // 60))
        return ClosingInfo("soon", hours=total_minutes // 60, minutes=total_minutes % 60)
    if (deadline_day - today).days == 1:
        return ClosingInfo("tomorrow")
    return ClosingInfo("later", day=deadline_day)


# --- Compte à rebours jusqu'à la clôture (« 2 j 4 h », « 1 h 42 », « 8 min ») ---

@dataclass(frozen=True)
class Countdown:
    days: int
    hours: int
    minutes: int


def countdown_to_closing(kickoff_at: datetime, now: datetime) -> Countdown:
    """Temps restant avant la clôture du pronostic, arrondi à la minute (1 min au minimum)."""
    remaining = max(prediction_deadline(kickoff_at) - now, timedelta(0))
    total_minutes = max(1, int(remaining.total_seconds() // 60))
    return Countdown(total_minutes // (24 * 60), total_minutes // 60 % 24, total_minutes % 60)
