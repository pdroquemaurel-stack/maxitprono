"""Import des pourcentages 1 / N / 2 du fournisseur, lancé avec l'import quotidien."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match
from app.models.match import MatchStatus
from app.providers.base import FootballProvider

DAYS_AHEAD = 3  # pronostics du fournisseur plus fiables près du match
MAX_CALLS = 20  # un appel par match chez API-Football : on protège le quota quotidien


def matches_without_probabilities(db: Session, provider_name: str, now: datetime) -> list[Match]:
    """Matchs à venir du fournisseur, dans les 3 prochains jours, sans pourcentages."""
    query = (select(Match)
             .where(Match.provider == provider_name,
                    Match.status == MatchStatus.SCHEDULED,
                    Match.prob_home.is_(None),
                    Match.kickoff_at > now,
                    Match.kickoff_at <= now + timedelta(days=DAYS_AHEAD))
             .order_by(Match.kickoff_at)
             .limit(MAX_CALLS))
    return list(db.scalars(query))


def import_probabilities(db: Session, provider: FootballProvider, now: datetime) -> int:
    """Renvoie le nombre de matchs complétés."""
    count = 0
    for match in matches_without_probabilities(db, provider.name, now):
        values = provider.get_probabilities(match.external_id)
        if values is None:
            continue
        match.prob_home, match.prob_draw, match.prob_away = values
        db.commit()  # au fil de l'eau : une erreur plus loin ne fait pas perdre le reste
        count += 1
    return count
