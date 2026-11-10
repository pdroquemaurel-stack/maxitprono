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


def group_by_day(matches: list, tz: tzinfo) -> list[tuple[date, list]]:
    """[(jour, [matchs])] dans l'ordre des coups d'envoi (matchs déjà triés)."""
    return [(day, list(items))
            for day, items in groupby(matches, key=lambda m: local_day(m.kickoff_at, tz))]
