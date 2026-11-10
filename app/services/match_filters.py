"""Filtres de la page Pronos : compétition et statut, état affiché sur chaque match.

Fonctions pures : aucune base, aucun réseau. Le même tri est refait en JavaScript
(static/js/matches.js) pour changer de filtre sans recharger la page.
"""
import re
import unicodedata
from datetime import datetime, timedelta

from app.models.match import MatchStatus

STATUS_FILTERS = ("todo", "mine", "all")  # À jouer, Mes pronos, Tous
DEFAULT_STATUS = "todo"
ALL_COMPETITIONS = "all"
CLOSING_SOON = timedelta(hours=24)  # en dessous : pastille « Ferme dans X h Y »

# Codes courts connus, par identifiant football-data.org puis par nom
_CODES_BY_ID = {"FL1": "L1", "BL1": "BL", "PD": "LIGA", "SA": "SA", "PL": "PL", "CL": "CL",
                "DED": "ERE", "PPL": "LP", "ELC": "CH", "EC": "EURO", "WC": "CM"}
_CODES_BY_NAME = {"ligue 1": "L1", "bundesliga": "BL", "primera division": "LIGA",
                  "la liga": "LIGA", "liga": "LIGA", "serie a": "SA", "premier league": "PL",
                  "uefa champions league": "CL", "ligue des champions": "CL",
                  "champions league": "CL"}


def competition_code(external_id: str, name: str) -> str:
    """Code court affiché à défaut d'emblème : « L1 », « PL », « CL »…"""
    if external_id in _CODES_BY_ID:
        return _CODES_BY_ID[external_id]
    if name.strip().lower() in _CODES_BY_NAME:
        return _CODES_BY_NAME[name.strip().lower()]
    words = [w for w in re.split(r"[\s\-.'’]+", name) if w]
    if len(words) >= 2:
        return "".join(w[0] for w in words[:3]).upper()
    return name[:3].upper() or "?"


def _ascii_key(code: str) -> str:
    """« DÉM » -> « dem » : clé sans accent, lisible dans l'adresse."""
    return unicodedata.normalize("NFKD", code).encode("ascii", "ignore").decode().lower()


def competition_keys(competitions: list[tuple[int, str]]) -> dict[int, str]:
    """{id: clé d'adresse} à partir de (id, code) : « l1 », « pl »…
    Deux compétitions au même code : on ajoute l'id pour les distinguer."""
    competitions = [(comp_id, _ascii_key(code)) for comp_id, code in competitions]
    codes = [code for _, code in competitions]
    return {comp_id: code if codes.count(code) == 1 else f"{code}{comp_id}"
            for comp_id, code in competitions}


def parse_status(value: str | None) -> str:
    return value if value in STATUS_FILTERS else DEFAULT_STATUS


def is_todo(is_open: bool, has_prediction: bool) -> bool:
    """« À jouer » : encore ouvert et sans prono."""
    return is_open and not has_prediction


def is_mine(status: str, has_prediction: bool) -> bool:
    """« Mes pronos » : un prono saisi sur un match pas encore terminé (modifiable ou en cours)."""
    return has_prediction and status not in (MatchStatus.FINISHED, MatchStatus.CANCELLED)


def matches_status(status_filter: str, todo: bool, mine: bool) -> bool:
    if status_filter == "todo":
        return todo
    if status_filter == "mine":
        return mine
    return True


def match_state(status: str, kickoff_at: datetime, now: datetime, is_open: bool,
                has_prediction: bool) -> str:
    """Pastille d'état d'un match : cancelled, live, finished, saved, postponed, closing, todo ou closed."""
    if status == MatchStatus.CANCELLED:
        return "cancelled"
    if status == MatchStatus.LIVE:
        return "live"
    if status == MatchStatus.FINISHED:
        return "finished"
    if not is_open:
        return "closed"
    if has_prediction:
        return "saved"
    if status == MatchStatus.POSTPONED:
        return "postponed"
    if kickoff_at - now < CLOSING_SOON:
        return "closing"
    return "todo"
