"""Client API-Football (https://www.api-football.com).

Chaque appel est enregistré dans ApiCallLog pour suivre le quota.
Les fonctions parse_* convertissent les réponses à notre format (voir base.py).
"""
import json
import re
from datetime import date, datetime

import httpx
from sqlalchemy.orm import Session

from app.models import ApiCallLog
from app.models.match import MatchStatus
from app.providers import API_FOOTBALL
from app.providers.base import ProviderError, parse_minute, save_call_log
from app.services.probabilities import round_to_100

BASE_URL = "https://v3.football.api-sports.io"

# Compétitions visées par le POC : identifiants API-Football connus
POC_LEAGUE_IDS = {
    "CAN": 6,
    "Ligue des champions CAF": 12,
    "Ligue des champions UEFA": 2,
    "Premier League": 39,
    "Liga": 140,
    "Ligue 1": 61,
    "Serie A": 135,
    "Bundesliga": 78,
}
# Championnats locaux : identifiants inconnus, on cherche par pays
POC_COUNTRIES = ["Cameroon", "Burkina-Faso"]

# Ballon en jeu : seuls ces codes ont une minute (pas la mi-temps, les pauses, les tirs au but)
_PLAYING_CODES = ("1H", "2H", "ET", "LIVE")

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


class ApiFootballError(ProviderError):
    pass


class ApiFootballClient:
    name = API_FOOTBALL

    def __init__(self, api_key: str, db: Session, http: httpx.Client | None = None):
        if not api_key:
            raise ApiFootballError("API_FOOTBALL_KEY manquante")
        self.api_key = api_key
        self.db = db
        self.http = http or httpx.Client(base_url=BASE_URL, timeout=15)

    # --- Interface FootballProvider ---

    def list_competitions(self) -> list[dict]:
        """Environ 10 appels : un par compétition connue, un par pays."""
        items = []
        for league_id in POC_LEAGUE_IDS.values():
            items += self.get_leagues(id=league_id)
        for country in POC_COUNTRIES:
            items += self.get_leagues(country=country)
        return [parse_league(item) for item in items]

    def get_matches(self, competition_id: str, season: int | None,
                    date_from: date, date_to: date) -> list[dict]:
        items = self.get_fixtures(competition_id, season, date_from.isoformat(),
                                  date_to.isoformat())
        return [parse_fixture(item) for item in items]

    def get_probabilities(self, match_id: str) -> tuple[int, int, int] | None:
        """Un appel par match (endpoint /predictions)."""
        items = self._get("predictions", {"fixture": match_id})
        return parse_prediction_percent(items[0]) if items else None

    # --- Appels bruts ---

    def get_status(self) -> dict:
        """Offre et quota du compte (cet appel ne consomme pas de quota)."""
        return self._get("status", {})

    def get_leagues(self, **filters) -> list:
        """Compétitions, filtrées par exemple par country="Cameroon" ou search="Elite"."""
        return self._get("leagues", filters)

    def get_fixtures(self, league: int | str, season: int | None, date_from: str,
                     date_to: str) -> list:
        """Matchs d'une compétition entre deux dates (format AAAA-MM-JJ)."""
        params = {"league": league, "from": date_from, "to": date_to}
        if season is not None:
            params["season"] = season
        return self._get("fixtures", params)

    def _get(self, endpoint: str, params: dict):
        log = ApiCallLog(provider=self.name, endpoint=endpoint,
                         params=json.dumps(params, sort_keys=True))
        try:
            response = self.http.get(
                f"/{endpoint}", params=params, headers={"x-apisports-key": self.api_key}
            )
        except httpx.HTTPError as exc:
            save_call_log(self.db, log, error=f"Erreur réseau : {exc}")
            raise ApiFootballError(f"API-Football injoignable : {exc}") from exc

        log.status_code = response.status_code
        log.requests_remaining = _remaining_quota(response)
        error = _extract_error(response)
        save_call_log(self.db, log, error=error)
        if error:
            raise ApiFootballError(f"Erreur API-Football sur /{endpoint} : {error}")
        return response.json()["response"]


def _remaining_quota(response: httpx.Response) -> int | None:
    value = response.headers.get("x-ratelimit-requests-remaining")
    return int(value) if value and value.isdigit() else None


def _extract_error(response: httpx.Response) -> str:
    """Message d'erreur, ou chaîne vide si tout va bien.

    L'API renvoie souvent un code 200 avec les erreurs dans le champ "errors"
    (liste vide ou dictionnaire selon les cas).
    """
    if response.status_code != 200:
        return f"HTTP {response.status_code}"
    try:
        errors = response.json().get("errors")
    except ValueError:
        return "Réponse non JSON"
    if not errors:
        return ""
    return "; ".join(f"{k}: {v}" for k, v in errors.items()) if isinstance(errors, dict) else str(errors)


# --- Conversion des réponses (fonctions pures) ---

def map_fixture_status(code: str) -> MatchStatus:
    """Statut simplifié ; un code inconnu est traité comme « à venir »."""
    return _STATUS_BY_CODE.get(code, MatchStatus.SCHEDULED)


def parse_round(text: str | None) -> int | None:
    """« Regular Season - 12 » ou « League Stage - 5 » -> 12 ou 5 ; « Round of 16 » -> None."""
    match = re.search(r" - (\d+)$", text or "")
    return int(match.group(1)) if match else None


def parse_fixture(item: dict) -> dict:
    """Champs d'un Match à partir d'un élément de la réponse /fixtures."""
    fixture, teams, goals = item["fixture"], item["teams"], item["goals"]
    return {
        "provider": API_FOOTBALL,
        "external_id": str(fixture["id"]),
        "season": item["league"]["season"],
        "matchday": parse_round(item["league"].get("round")),
        "kickoff_at": datetime.fromisoformat(fixture["date"]),  # l'API fournit le fuseau
        "status": map_fixture_status(fixture["status"]["short"]),
        "home_team": teams["home"]["name"],
        "away_team": teams["away"]["name"],
        "home_logo_url": teams["home"].get("logo") or "",
        "away_logo_url": teams["away"].get("logo") or "",
        # Score final, prolongations comprises (hors tirs au but)
        "home_score": goals["home"],
        "away_score": goals["away"],
        "minute": (parse_minute(fixture["status"].get("elapsed"))
                   if fixture["status"]["short"] in _PLAYING_CODES else None),
    }


def parse_prediction_percent(item: dict) -> tuple[int, int, int] | None:
    """Pourcentages de /predictions (« 45% »), ramenés à une somme de 100."""
    percent = (item.get("predictions") or {}).get("percent") or {}
    try:
        values = [float(str(percent[k]).rstrip("%")) for k in ("home", "draw", "away")]
    except (KeyError, ValueError):
        return None
    if sum(values) <= 0:
        return None
    return tuple(round_to_100(values))


def parse_league(item: dict) -> dict:
    """Compétition renvoyée par /leagues : saison en cours (sinon la dernière) et couverture."""
    seasons = item.get("seasons") or []
    current = next((s for s in seasons if s.get("current")), seasons[-1] if seasons else {})
    coverage = current.get("coverage") or {}
    events = bool((coverage.get("fixtures") or {}).get("events"))
    return {
        "external_id": str(item["league"]["id"]),
        "name": item["league"]["name"],
        "country": item["country"]["name"],
        "logo_url": item["league"].get("logo") or "",
        "season": current.get("year"),
        "is_current": bool(current.get("current")),
        "start": current.get("start", ""),
        "end": current.get("end", ""),
        "coverage": f"événements {_yes_no(events)} · "
                    f"pronos {_yes_no(coverage.get('predictions'))} · "
                    f"cotes {_yes_no(coverage.get('odds'))}",
    }


def _yes_no(value) -> str:
    return "oui" if value else "non"
