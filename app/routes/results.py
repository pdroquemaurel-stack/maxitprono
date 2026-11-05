"""Onglet Résultats : matchs terminés, avec mon pronostic et mes points."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import current_user
from app.db import get_db
from app.models import Competition, Match, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.routes.matches import predictions_by_match
from app.services import league_store
from app.services.deadlines import is_prediction_open
from app.services.leagues import pick_league, sort_league_predictions
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()

RESULTS_DAYS = 14
DONE_STATUSES = (MatchStatus.FINISHED, MatchStatus.CANCELLED)


def recent_results(db: Session, now: datetime) -> list[Match]:
    """Matchs terminés ou annulés des 14 derniers jours, du plus récent au plus ancien."""
    query = (select(Match).join(Match.competition).options(joinedload(Match.competition))
             .where(Competition.is_active.is_(True),
                    Match.status.in_(DONE_STATUSES),
                    Match.kickoff_at >= now - timedelta(days=RESULTS_DAYS))
             .order_by(Match.kickoff_at.desc()))
    return list(db.scalars(query))


@router.get("/results")
def results_page(request: Request, db: Session = Depends(get_db),
                 user: User | None = Depends(current_user)):
    now = utc_now()
    matches = recent_results(db, now)
    tz = resolve_timezone(request.cookies.get("tz"))
    context = {
        "user": user,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "matches": matches,
        "predictions": predictions_by_match(db, user, [m.id for m in matches]),
    }
    return templates.TemplateResponse(request, "results.html", context)


@router.get("/results/{match_id}")
def result_page(match_id: int, request: Request, db: Session = Depends(get_db),
                user: User | None = Depends(current_user)):
    """Match clôturé : score final, résultat de mon pronostic et pronos de ma ligue."""
    match = db.get(Match, match_id)
    if match is None or match.status not in DONE_STATUSES:
        raise HTTPException(status_code=404)
    league, picks = league_picks(request, db, user, match)
    context = {
        "user": user,
        "tz": resolve_timezone(request.cookies.get("tz")),
        "match": match,
        "prediction": predictions_by_match(db, user, [match.id]).get(match.id),
        "league": league,
        "league_picks": picks,
    }
    return templates.TemplateResponse(request, "result.html", context)


def league_picks(request: Request, db: Session, user: User | None, match: Match) -> tuple:
    """Ligue choisie sur l'accueil et pronos de ses membres, seulement après la clôture."""
    if user is None or is_prediction_open(match.status, match.kickoff_at, utc_now()):
        return None, []
    leagues = league_store.my_leagues(db, user.id)
    league_id = pick_league([league.id for league, _ in leagues], request.cookies.get("league"))
    if league_id is None:
        return None, []
    league = next(league for league, _ in leagues if league.id == league_id)
    rows = league_store.match_predictions(db, league_id, match.id)
    return league, sort_league_predictions(rows, user.id)
