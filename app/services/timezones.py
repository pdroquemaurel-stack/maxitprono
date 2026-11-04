"""Fuseau horaire du joueur et regroupement des matchs par jour local.

Le navigateur envoie son fuseau dans le cookie `tz` (ex. "Africa/Ouagadougou").
Fonctions pures.
"""
from datetime import date, datetime
from itertools import groupby
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Africa/Douala"  # avant que le navigateur ait envoyé le sien


def resolve_timezone(name: str | None) -> ZoneInfo:
    """Fuseau demandé s'il est connu, sinon le fuseau par défaut."""
    try:
        return ZoneInfo(name) if name else ZoneInfo(DEFAULT_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(DEFAULT_TIMEZONE)


def local_day(moment: datetime, tz: ZoneInfo) -> date:
    return moment.astimezone(tz).date()


def group_by_day_and_competition(matches: list, tz: ZoneInfo) -> list[tuple[date, list]]:
    """[(jour, [(compétition, [matchs])])], dans l'ordre des coups d'envoi.

    Les matchs doivent arriver triés par coup d'envoi.
    """
    days = []
    for day, day_matches in groupby(matches, key=lambda m: local_day(m.kickoff_at, tz)):
        day_matches = sorted(day_matches, key=lambda m: (m.competition.name, m.kickoff_at))
        competitions = [(competition, list(items)) for competition, items
                        in groupby(day_matches, key=lambda m: m.competition)]
        days.append((day, competitions))
    return days
