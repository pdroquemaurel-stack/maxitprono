"""Ce que l'app attend d'un fournisseur de données foot.

Les fournisseurs renvoient des dictionnaires déjà convertis à notre format :
- compétition : external_id, name, country, logo_url, season, is_current,
  start, end, coverage (texte libre affiché par scripts/check_coverage) ;
- match : les champs d'un Match (provider, external_id, season, kickoff_at,
  status, home_team, away_team, home_logo_url, away_logo_url, home_score, away_score).
"""
from datetime import date
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import ApiCallLog


class ProviderError(Exception):
    """Fournisseur injoignable, clé manquante ou réponse en erreur."""


class FootballProvider(Protocol):
    name: str  # valeur de la colonne `provider`

    def list_competitions(self) -> list[dict]:
        """Compétitions visées par le POC et couvertes par le fournisseur."""
        ...

    def get_matches(self, competition_id: str, season: int | None,
                    date_from: date, date_to: date) -> list[dict]:
        """Matchs d'une compétition entre deux dates (incluses)."""
        ...


def save_call_log(db: Session, log: ApiCallLog, error: str = "") -> None:
    """Enregistre l'appel tout de suite : il doit rester journalisé même si la suite échoue."""
    log.error = error
    db.add(log)
    db.commit()
