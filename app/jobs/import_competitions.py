"""Import de la liste des compétitions du fournisseur (toutes inactives par défaut)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition
from app.providers.base import FootballProvider


def save_competition(db: Session, provider_name: str, summary: dict) -> Competition:
    """Crée ou met à jour la compétition, sans toucher à son activation."""
    competition = db.scalar(select(Competition).where(
        Competition.provider == provider_name,
        Competition.external_id == summary["external_id"]))
    if competition is None:
        competition = Competition(provider=provider_name, external_id=summary["external_id"],
                                  is_active=False)
        db.add(competition)
    competition.name = summary["name"]
    competition.country = summary["country"]
    competition.logo_url = summary["logo_url"]
    competition.season = summary["season"]
    return competition


def import_competitions(db: Session, provider: FootballProvider) -> list[dict]:
    """Enregistre les compétitions du fournisseur et renvoie leurs résumés."""
    summaries = provider.list_competitions()
    for summary in summaries:
        save_competition(db, provider.name, summary)
    db.commit()
    return summaries
