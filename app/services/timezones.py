"""Fuseau horaire du joueur et regroupement des matchs par jour local.

Le navigateur envoie son fuseau dans le cookie `tz` (ex. "Africa/Ouagadougou").
Fonctions pures.
"""
from datetime import UTC, date, datetime, tzinfo
from itertools import groupby
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Africa/Douala"  # avant que le navigateur ait envoyé le sien


def resolve_timezone(name: str | None) -> tzinfo:
    """Fuseau demandé s'il est connu, sinon le fuseau par défaut, sinon UTC.

    UTC en dernier recours : si le serveur n'a pas la base des fuseaux horaires.
    """
    for candidate in (name, DEFAULT_TIMEZONE):
        try:
            if candidate:
                return ZoneInfo(candidate)
        except (ZoneInfoNotFoundError, ValueError):
            continue
    return UTC


def local_day(moment: datetime, tz: tzinfo) -> date:
    return moment.astimezone(tz).date()


def group_by_day_and_competition(matches: list, tz: tzinfo) -> list[tuple[date, list]]:
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
