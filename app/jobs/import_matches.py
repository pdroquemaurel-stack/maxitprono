"""Tâches d'import : matchs à venir (1 fois par jour) et scores en direct.

Ces fonctions reçoivent la session et le client : elles sont appelées
par les scripts, et plus tard par la route protégée de déclenchement.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Competition, Match
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.providers.api_football import ApiFootballClient
from app.services.fixtures import needs_score_update, parse_fixture

DAYS_BACK = 3  # rattrape les matchs restés sans score final
DAYS_AHEAD = 14


def upsert_match(db: Session, competition: Competition, fields: dict) -> Match:
    """Crée le match ou met à jour celui qui a le même identifiant API."""
    match = db.scalar(select(Match).where(Match.api_id == fields["api_id"]))
    if match is None:
        match = Match(competition=competition)
        db.add(match)
    for name, value in fields.items():
        setattr(match, name, value)
    match.synced_at = utc_now()
    return match


def import_matches(db: Session, client: ApiFootballClient, date_from: date, date_to: date,
                   season: int | None = None) -> int:
    """Importe les matchs des compétitions actives entre deux dates.

    `season` force une saison (ex. 2024 pour tester avec l'offre gratuite) ;
    sinon, la saison enregistrée pour chaque compétition est utilisée.
    """
    competitions = db.scalars(select(Competition).where(Competition.is_active)).all()
    count = 0
    for competition in competitions:
        items = client.get_fixtures(competition.api_id, season or competition.season,
                                    date_from.isoformat(), date_to.isoformat())
        for item in items:
            upsert_match(db, competition, parse_fixture(item))
            count += 1
        db.commit()
    return count


def import_upcoming_matches(db: Session, client: ApiFootballClient, today: date) -> int:
    """Tâche quotidienne : de J-3 à J+14."""
    return import_matches(db, client, today - timedelta(days=DAYS_BACK),
                          today + timedelta(days=DAYS_AHEAD))


def update_live_scores(db: Session, client: ApiFootballClient, now: datetime) -> int:
    """Met à jour les matchs en cours ; aucun appel API s'il n'y en a pas.

    Un appel par compétition et par jour concerné (le paramètre `ids` de l'API,
    plus économe, n'est pas disponible avec l'offre gratuite).
    """
    candidates = db.scalars(
        select(Match).where(
            Match.api_id.is_not(None),
            Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.LIVE]),
            Match.kickoff_at <= now,
        )
    ).all()
    to_update = [m for m in candidates if needs_score_update(m.status, m.kickoff_at, now)]

    groups: dict[tuple, list[Match]] = {}
    for match in to_update:
        key = (match.competition, match.season, match.kickoff_at.date())
        groups.setdefault(key, []).append(match)

    for (competition, season, day), matches in groups.items():
        wanted = {m.api_id for m in matches}
        items = client.get_fixtures(competition.api_id, season, day.isoformat(), day.isoformat())
        for item in items:
            if item["fixture"]["id"] in wanted:
                upsert_match(db, competition, parse_fixture(item))
        db.commit()
    return len(to_update)
