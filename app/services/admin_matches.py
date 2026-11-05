"""Saisies du back-office sur les matchs : correction de score, ajout à la main.

Fonctions pures : aucune base. Les erreurs sont des clés de traduction.
"""
from datetime import UTC, date, datetime, time, tzinfo

from app.models.match import MatchStatus
from app.services.predictions import parse_score

STATUSES = [MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.FINISHED,
            MatchStatus.POSTPONED, MatchStatus.CANCELLED]
TEAM_MAX = 120


def parse_correction(status: str, home: str, away: str) -> tuple[dict | None, str | None]:
    """{status, home_score, away_score} corrigés, ou (None, erreur).

    Terminé : les deux scores sont obligatoires. Sinon ils peuvent rester vides
    (score en cours facultatif, match à venir, reporté ou annulé).
    """
    if status not in STATUSES:
        return None, "error_status"
    if not home.strip() and not away.strip():
        if status == MatchStatus.FINISHED:
            return None, "error_final_score_required"
        return {"status": status, "home_score": None, "away_score": None}, None
    home_score, away_score = parse_score(home), parse_score(away)
    if home_score is None or away_score is None:
        return None, "error_score_format"
    return {"status": status, "home_score": home_score, "away_score": away_score}, None


def parse_new_match(home_team: str, away_team: str, day: str, hour: str,
                    tz: tzinfo) -> tuple[dict | None, str | None]:
    """Champs d'un match ajouté à la main ; l'heure est saisie dans le fuseau de l'admin."""
    home_team, away_team = " ".join(home_team.split()), " ".join(away_team.split())
    if not home_team or not away_team or max(len(home_team), len(away_team)) > TEAM_MAX:
        return None, "error_team_name"
    if home_team.lower() == away_team.lower():
        return None, "error_same_teams"
    try:
        local = datetime.combine(date.fromisoformat(day), time.fromisoformat(hour), tzinfo=tz)
    except ValueError:
        return None, "error_kickoff"
    return {"home_team": home_team, "away_team": away_team,
            "kickoff_at": local.astimezone(UTC)}, None
