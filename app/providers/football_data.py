"""Client football-data.org, API v4 (https://www.football-data.org/documentation/api).

Offre gratuite : 12 compétitions (grands championnats européens, Ligue des
champions, Euro, Coupe du monde…), 10 appels par minute, ni cotes ni pronostics.
Chaque appel est enregistré dans ApiCallLog.
"""
import json
from datetime import date, datetime

import httpx
from sqlalchemy.orm import Session

from app.models import ApiCallLog
from app.models.match import MatchStatus
from app.providers import FOOTBALL_DATA
from app.providers.base import ProviderError, parse_minute, save_call_log

BASE_URL = "https://api.football-data.org/v4"

# Compétitions visées par le POC, par code football-data (servent d'identifiant)
POC_COMPETITION_CODES = ["CL", "PL", "PD", "FL1", "SA", "BL1"]

# https://docs.football-data.org/general/v4/match.html
_STATUS_BY_CODE = {
    "SCHEDULED": MatchStatus.SCHEDULED,  # date connue, heure pas encore
    "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.LIVE,  # mi-temps
    "LIVE": MatchStatus.LIVE,
    "SUSPENDED": MatchStatus.LIVE,  # peut reprendre (comme SUSP chez API-Football)
    "FINISHED": MatchStatus.FINISHED,
    "AWARDED": MatchStatus.FINISHED,  # victoire sur tapis vert
    "POSTPONED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.CANCELLED,
}


class FootballDataError(ProviderError):
    pass


class FootballDataClient:
    name = FOOTBALL_DATA

    def __init__(self, api_key: str, db: Session, http: httpx.Client | None = None):
        if not api_key:
            raise FootballDataError("FOOTBALL_DATA_API_KEY manquante")
        self.api_key = api_key
        self.db = db
        self.http = http or httpx.Client(base_url=BASE_URL, timeout=15)

    def list_competitions(self) -> list[dict]:
        """Un seul appel ; ne garde que les compétitions du POC."""
        items = self._get("competitions", {})["competitions"]
        return [parse_competition(item) for item in items
                if item.get("code") in POC_COMPETITION_CODES]

    def get_matches(self, competition_id: str, season: int | None,
                    date_from: date, date_to: date) -> list[dict]:
        params = {"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat()}
        if season is not None:
            params["season"] = season
        items = self._get(f"competitions/{competition_id}/matches", params)["matches"]
        return [parse_match(item) for item in items]

    def get_probabilities(self, match_id: str) -> None:
        """Pas de prédictions ni de cotes sur l'offre gratuite : aucun appel."""
        return None

    def _get(self, path: str, params: dict) -> dict:
        log = ApiCallLog(provider=self.name, endpoint=path,
                         params=json.dumps(params, sort_keys=True))
        try:
            response = self.http.get(f"/{path}", params=params,
                                     headers={"X-Auth-Token": self.api_key})
        except httpx.HTTPError as exc:
            save_call_log(self.db, log, error=f"Erreur réseau : {exc}")
            raise FootballDataError(f"football-data.org injoignable : {exc}") from exc

        log.status_code = response.status_code
        log.requests_remaining = _remaining_per_minute(response)
        error = _extract_error(response)
        save_call_log(self.db, log, error=error)
        if error:
            raise FootballDataError(f"Erreur football-data.org sur /{path} : {error}")
        return response.json()


def _remaining_per_minute(response: httpx.Response) -> int | None:
    value = response.headers.get("X-Requests-Available-Minute")
    return int(value) if value and value.isdigit() else None


def _extract_error(response: httpx.Response) -> str:
    """Message d'erreur, ou chaîne vide si tout va bien."""
    if response.status_code == 200:
        return ""
    try:
        message = response.json().get("message", "")
    except ValueError:
        message = ""
    return f"HTTP {response.status_code} {message}".strip()


# --- Conversion des réponses (fonctions pures) ---

def map_match_status(code: str) -> MatchStatus:
    """Statut simplifié ; un code inconnu est traité comme « à venir »."""
    return _STATUS_BY_CODE.get(code, MatchStatus.SCHEDULED)


def final_score(score: dict) -> tuple[int | None, int | None]:
    """Score prolongations comprises, hors tirs au but.

    En v4, `fullTime` inclut les tirs au but quand il y en a eu : on les retire.
    """
    home, away = score["fullTime"]["home"], score["fullTime"]["away"]
    penalties = score.get("penalties") or {}
    if score.get("duration") == "PENALTY_SHOOTOUT" and penalties.get("home") is not None:
        home, away = home - penalties["home"], away - penalties["away"]
    return home, away


def parse_match(item: dict) -> dict:
    """Champs d'un Match à partir d'un élément de la réponse /matches."""
    home, away = item["homeTeam"], item["awayTeam"]
    home_score, away_score = final_score(item["score"])
    return {
        "provider": FOOTBALL_DATA,
        "external_id": str(item["id"]),
        "season": _season_year(item.get("season") or {}),
        "matchday": item.get("matchday"),  # vide en phase à élimination directe
        "kickoff_at": datetime.fromisoformat(item["utcDate"]),  # en UTC (suffixe Z)
        "status": map_match_status(item["status"]),
        "home_team": home.get("shortName") or home["name"],
        "away_team": away.get("shortName") or away["name"],
        "home_logo_url": home.get("crest") or "",
        "away_logo_url": away.get("crest") or "",
        "home_score": home_score,
        "away_score": away_score,
        # Absente de l'offre gratuite (vérifié le 10 novembre 2026) : le match reste « En direct »
        "minute": parse_minute(item.get("minute")) if item["status"] == "IN_PLAY" else None,
    }


def parse_competition(item: dict) -> dict:
    """Compétition renvoyée par /competitions, avec sa saison en cours."""
    season = item.get("currentSeason") or {}
    return {
        "external_id": item["code"],
        "name": item["name"],
        "country": (item.get("area") or {}).get("name", ""),
        "logo_url": item.get("emblem") or "",
        "season": _season_year(season),
        "is_current": bool(season),
        "start": season.get("startDate", ""),
        "end": season.get("endDate", ""),
        "coverage": "",
    }


def _season_year(season: dict) -> int | None:
    """Année de début de saison, comme chez API-Football (2026 pour 2026-2027)."""
    start = season.get("startDate")
    return int(start[:4]) if start else None
