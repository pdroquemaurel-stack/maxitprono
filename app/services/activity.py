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
    user_id: int = 0  # pour l'avatar
    has_photo: bool = False
    league: str = ""  # nom de la ligue, pour le fil « Chez les copains » de l'accueil


def join_event(nickname: str, joined_at: datetime, is_owner: bool, user_id: int = 0,
               has_photo: bool = False) -> Event:
    return Event("created" if is_owner else "joined", nickname, joined_at,
                 user_id=user_id, has_photo=has_photo)


def exact_event(nickname: str, home_team: str, away_team: str, kickoff_at: datetime,
                user_id: int = 0, has_photo: bool = False) -> Event:
    return Event("exact", nickname, kickoff_at, f"{home_team} – {away_team}",
                 user_id=user_id, has_photo=has_photo)


def latest_events(events: list[Event], now: datetime) -> list[Event]:
    """Les 5 événements les plus récents des 7 derniers jours, du plus récent au plus ancien."""
    recent = [e for e in events if now - ACTIVITY_WINDOW <= e.at <= now]
    return sorted(recent, key=lambda e: e.at, reverse=True)[:ACTIVITY_LIMIT]


FRIENDS_FEED_LIMIT = 3


def friends_feed(events: list[Event], me_id: int, limit: int = FRIENDS_FEED_LIMIT) -> list[Event]:
    """Fil « Chez les copains » : événements de toutes mes ligues, sans les miens,
    sans doublon (un même score exact vu dans deux ligues), du plus récent au plus ancien."""
    seen, feed = set(), []
    for event in sorted(events, key=lambda e: e.at, reverse=True):
        key = (event.kind, event.user_id, event.match, event.at)
        if event.user_id == me_id or key in seen:
            continue
        seen.add(key)
        feed.append(event)
    return feed[:limit]
