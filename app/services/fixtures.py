"""Conversion des données API-Football et choix des matchs à mettre à jour.

Fonctions pures : aucune base, aucun réseau.
"""
from datetime import datetime, timedelta

from app.models.match import MatchStatus

# Codes "short" de l'API -> nos statuts
# https://www.api-football.com/documentation-v3#tag/Fixtures
_STATUS_BY_CODE = {
    "TBD": MatchStatus.SCHEDULED,
    "NS": MatchStatus.SCHEDULED,
    "1H": MatchStatus.LIVE,
    "HT": MatchStatus.LIVE,
    "2H": MatchStatus.LIVE,
    "ET": MatchStatus.LIVE,
    "BT": MatchStatus.LIVE,
    "P": MatchStatus.LIVE,
    "SUSP": MatchStatus.LIVE,  # suspendu : peut reprendre
    "INT": MatchStatus.LIVE,  # interrompu : peut reprendre
    "LIVE": MatchStatus.LIVE,
    "FT": MatchStatus.FINISHED,
    "AET": MatchStatus.FINISHED,
    "PEN": MatchStatus.FINISHED,
    "AWD": MatchStatus.FINISHED,  # victoire sur tapis vert
    "WO": MatchStatus.FINISHED,  # forfait
    "PST": MatchStatus.POSTPONED,
    "CANC": MatchStatus.CANCELLED,
    "ABD": MatchStatus.CANCELLED,  # abandonné
}

# Au-delà, un match commencé est considéré comme terminé côté mise à jour
LIVE_WINDOW = timedelta(hours=3)


def map_fixture_status(code: str) -> MatchStatus:
    """Statut simplifié ; un code inconnu est traité comme « à venir »."""
    return _STATUS_BY_CODE.get(code, MatchStatus.SCHEDULED)


def parse_fixture(item: dict) -> dict:
    """Champs d'un Match à partir d'un élément de la réponse /fixtures."""
    fixture, teams, goals = item["fixture"], item["teams"], item["goals"]
    return {
        "api_id": fixture["id"],
        "season": item["league"]["season"],
        "kickoff_at": datetime.fromisoformat(fixture["date"]),  # l'API fournit le fuseau
        "status": map_fixture_status(fixture["status"]["short"]),
        "home_team": teams["home"]["name"],
        "away_team": teams["away"]["name"],
        "home_logo_url": teams["home"].get("logo") or "",
        "away_logo_url": teams["away"].get("logo") or "",
        # Score final, prolongations comprises (hors tirs au but)
        "home_score": goals["home"],
        "away_score": goals["away"],
    }


def needs_score_update(status: str, kickoff_at: datetime, now: datetime) -> bool:
    """Vrai si le match est en cours ou vient de commencer sans être terminé."""
    if status == MatchStatus.LIVE:
        return True
    return status == MatchStatus.SCHEDULED and kickoff_at <= now <= kickoff_at + LIVE_WINDOW

