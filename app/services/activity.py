"""Fil d'activité d'une ligue (« Dans la ligue » sur l'accueil). Fonctions pures."""
from dataclasses import dataclass
from datetime import datetime, timedelta

ACTIVITY_WINDOW = timedelta(days=7)
ACTIVITY_LIMIT = 5


@dataclass(frozen=True)
class Event:
    kind: str  # "created", "joined" ou "exact"
    nickname: str
    at: datetime
    match: str = ""  # « Coton Sport – Canon » pour un score exact


def join_event(nickname: str, joined_at: datetime, is_owner: bool) -> Event:
    return Event("created" if is_owner else "joined", nickname, joined_at)


def exact_event(nickname: str, home_team: str, away_team: str, kickoff_at: datetime) -> Event:
    return Event("exact", nickname, kickoff_at, f"{home_team} – {away_team}")


def latest_events(events: list[Event], now: datetime) -> list[Event]:
    """Les 5 événements les plus récents des 7 derniers jours, du plus récent au plus ancien."""
    recent = [e for e in events if now - ACTIVITY_WINDOW <= e.at <= now]
    return sorted(recent, key=lambda e: e.at, reverse=True)[:ACTIVITY_LIMIT]
