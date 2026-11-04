"""Liste des matchs, saisie des pronostics, historique du joueur."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import current_user, require_user
from app.db import get_db
from app.models import Competition, Match, Prediction, User
from app.models.types import utc_now
from app.services.deadlines import is_prediction_open
from app.services.predictions import save_prediction
from app.services.timezones import group_by_day_and_competition, resolve_timezone
from app.templating import templates

router = APIRouter()

DAYS_AHEAD = 7
RECENT_WINDOW = timedelta(hours=3)  # garde visibles les matchs en cours ou juste finis
HOME_MATCH_COUNT = 5
HISTORY_LIMIT = 50
SAFE_RETURN_PAGES = ("/", "/matches")


# --- Lectures en base ---

def upcoming_matches(db: Session, now: datetime) -> list[Match]:
    """Matchs des compétitions actives, des 3 dernières heures aux 7 prochains jours."""
    query = (select(Match).join(Match.competition).options(joinedload(Match.competition))
             .where(Competition.is_active.is_(True),
                    Match.kickoff_at >= now - RECENT_WINDOW,
                    Match.kickoff_at <= now + timedelta(days=DAYS_AHEAD))
             .order_by(Match.kickoff_at))
    return list(db.scalars(query))


def predictions_by_match(db: Session, user: User | None, match_ids: list[int]) -> dict:
    if user is None or not match_ids:
        return {}
    query = select(Prediction).where(Prediction.user_id == user.id,
                                     Prediction.match_id.in_(match_ids))
    return {p.match_id: p for p in db.scalars(query)}


def match_context(request: Request, db: Session, user: User | None, matches: list[Match],
                  now: datetime) -> dict:
    """Données communes aux pages qui affichent des cartes de match."""
    tz = resolve_timezone(request.cookies.get("tz"))
    return {
        "user": user,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "predictions": predictions_by_match(db, user, [m.id for m in matches]),
        "open_ids": {m.id for m in matches if is_prediction_open(m.status, m.kickoff_at, now)},
        "saved_id": _int_or_none(request.query_params.get("saved")),
        "error_id": _int_or_none(request.query_params.get("match")),
        "error": _error_key(request.query_params.get("error")),
    }


def _error_key(value: str | None) -> str | None:
    """N'accepte dans l'URL que des clés d'erreur, pas du texte libre."""
    return value if value and value.startswith("error_") and value.isidentifier() else None


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


# --- Pages ---

@router.get("/matches")
def matches_page(request: Request, db: Session = Depends(get_db),
                 user: User | None = Depends(current_user)):
    now = utc_now()
    matches = upcoming_matches(db, now)
    context = match_context(request, db, user, matches, now)
    context["days"] = group_by_day_and_competition(matches, context["tz"])
    return templates.TemplateResponse(request, "matches.html", context)


@router.post("/matches/{match_id}/prediction")
def submit_prediction(match_id: int, db: Session = Depends(get_db),
                      user: User = Depends(require_user), home_score: str = Form(""),
                      away_score: str = Form(""), back: str = Form("/matches")):
    error = save_prediction(db, user.id, match_id, home_score, away_score, utc_now())
    back = back if back in SAFE_RETURN_PAGES else "/matches"
    query = f"error={error}&match={match_id}" if error else f"saved={match_id}"
    return RedirectResponse(f"{back}?{query}#m{match_id}", status_code=303)


def home_matches(db: Session, user: User, now: datetime) -> tuple[list[Match], int]:
    """Prochains matchs ouverts, et nombre de ceux qui n'ont pas encore de pronostic."""
    open_matches = [m for m in upcoming_matches(db, now)
                    if is_prediction_open(m.status, m.kickoff_at, now)]
    predicted = predictions_by_match(db, user, [m.id for m in open_matches])
    to_predict = sum(1 for m in open_matches if m.id not in predicted)
    return open_matches[:HOME_MATCH_COUNT], to_predict


def prediction_history(db: Session, user: User) -> list[Prediction]:
    query = (select(Prediction).join(Prediction.match)
             .options(joinedload(Prediction.match).joinedload(Match.competition))
             .where(Prediction.user_id == user.id)
             .order_by(Match.kickoff_at.desc()).limit(HISTORY_LIMIT))
    return list(db.scalars(query))
