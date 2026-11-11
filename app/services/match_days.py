"""Calendrier de la page Pronos : les N jours ouverts aux pronostics, à partir d'aujourd'hui.

N = réglage admin « Jours de matchs ouverts aux pronostics ». Fonctions pures.
"""
from collections.abc import Container
from datetime import date, datetime, time, timedelta, tzinfo

from app.models.match import MatchStatus
from app.services.deadlines import is_prediction_open
from app.services.timezones import local_day

# Matchs qui ne comptent pas dans l'état d'un jour : on ne peut pas (ou plus) les jouer
NOT_PLAYED = (MatchStatus.CANCELLED, MatchStatus.POSTPONED)


def calendar_days(today: date, count: int) -> list[date]:
    """Les `count` jours à partir d'aujourd'hui (au moins un : aujourd'hui)."""
    return [today + timedelta(days=offset) for offset in range(max(count, 1))]


def pick_day(wanted: str | None, days: list[date]) -> date:
    """Jour demandé dans l'adresse (?day=2026-11-12) s'il est dans le calendrier, sinon le premier."""
    try:
        day = date.fromisoformat(wanted or "")
    except ValueError:
        return days[0]
    return day if day in days else days[0]


def match_day(kickoff_at: datetime, tz: tzinfo, today: date) -> date:
    """Jour du calendrier d'un match : son jour local, ou aujourd'hui s'il a commencé la veille
    (match encore en cours ou juste fini après minuit)."""
    return max(local_day(kickoff_at, tz), today)


def calendar_end(days: list[date], tz: tzinfo) -> datetime:
    """Fin du dernier jour du calendrier (minuit suivant, heure locale du joueur)."""
    return datetime.combine(days[-1] + timedelta(days=1), time(0), tzinfo=tz)


def day_prediction_status(matches: list, predicted_ids: Container[int], now: datetime) -> str:
    """État des pronos du joueur sur un jour du calendrier, toutes compétitions confondues :

    - "none"   : aucun match (hors annulés et reportés) ;
    - "todo"   : au moins un match encore ouvert sans prono ;
    - "done"   : tous les matchs ont un prono ;
    - "missed" : des matchs sans prono, mais plus aucun n'est ouvert (rien à faire).
    """
    played = [m for m in matches if m.status not in NOT_PLAYED]
    if not played:
        return "none"
    missing = [m for m in played if m.id not in predicted_ids]
    if not missing:
        return "done"
    if any(is_prediction_open(m.status, m.kickoff_at, now) for m in missing):
        return "todo"
    return "missed"
