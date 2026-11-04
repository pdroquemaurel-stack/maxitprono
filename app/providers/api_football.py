"""Client API-Football : seul endroit de l'app qui appelle l'API.

Chaque appel est enregistré dans ApiCallLog pour suivre le quota.
"""
import json

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ApiCallLog

BASE_URL = "https://v3.football.api-sports.io"
MAX_IDS_PER_CALL = 20  # limite de l'API pour /fixtures?ids=


class ApiFootballError(Exception):
    pass


class ApiFootballClient:
    def __init__(self, api_key: str, db: Session, http: httpx.Client | None = None):
        if not api_key:
            raise ApiFootballError("API_FOOTBALL_KEY manquante")
        self.api_key = api_key
        self.db = db
        self.http = http or httpx.Client(base_url=BASE_URL, timeout=15)

    def get_status(self) -> dict:
        """Offre et quota du compte (cet appel ne consomme pas de quota)."""
        return self._get("status", {})

    def get_leagues(self, **filters) -> list:
        """Compétitions, filtrées par exemple par country="Cameroon" ou search="Elite"."""
        return self._get("leagues", filters)

    def get_fixtures(self, league: int, season: int, date_from: str, date_to: str) -> list:
        """Matchs d'une compétition entre deux dates (format AAAA-MM-JJ)."""
        params = {"league": league, "season": season, "from": date_from, "to": date_to}
        return self._get("fixtures", params)

    def get_fixtures_by_ids(self, ids: list[int]) -> list:
        """Jusqu'à 20 matchs en un seul appel."""
        if not 1 <= len(ids) <= MAX_IDS_PER_CALL:
            raise ValueError(f"Entre 1 et {MAX_IDS_PER_CALL} identifiants par appel")
        return self._get("fixtures", {"ids": "-".join(str(i) for i in ids)})

    def _get(self, endpoint: str, params: dict):
        log = ApiCallLog(endpoint=endpoint, params=json.dumps(params, sort_keys=True))
        try:
            response = self.http.get(
                f"/{endpoint}", params=params, headers={"x-apisports-key": self.api_key}
            )
        except httpx.HTTPError as exc:
            self._save_log(log, error=f"Erreur réseau : {exc}")
            raise ApiFootballError(f"API-Football injoignable : {exc}") from exc

        log.status_code = response.status_code
        log.requests_remaining = _remaining_quota(response)
        error = _extract_error(response)
        self._save_log(log, error=error)
        if error:
            raise ApiFootballError(f"Erreur API-Football sur /{endpoint} : {error}")
        return response.json()["response"]

    def _save_log(self, log: ApiCallLog, error: str = "") -> None:
        # Commit immédiat : l'appel doit rester journalisé même si la suite échoue
        log.error = error
        self.db.add(log)
        self.db.commit()


def make_client(db: Session) -> ApiFootballClient:
    return ApiFootballClient(settings.api_football_key, db)


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
