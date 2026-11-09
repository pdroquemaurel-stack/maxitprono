"""Liste des matchs, saisie des pronostics, historique du joueur."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import current_user, require_user
from app.db import get_db
from app.i18n import translate
from app.models import Competition, Match, Prediction, User
from app.models.types import utc_now
from app.services.deadlines import is_prediction_open
from app.services.predictions import save_prediction
from app.services.probabilities import match_probabilities
from app.services.settings_store import prediction_days_ahead
from app.services.timezones import group_by_day_and_competition, resolve_timezone
from app.templating import templates

router = APIRouter()

RECENT_WINDOW = timedelta(hours=3)  # garde visibles les matchs en cours ou juste finis
HISTORY_LIMIT = 50


# --- Lectures en base ---

def upcoming_matches(db: Session, now: datetime) -> list[Match]:
    """Matchs des compétitions actives, des 3 dernières heures aux N prochains jours (réglage admin)."""
    query = (select(Match).join(Match.competition).options(joinedload(Match.competition))
             .where(Competition.is_active.is_(True),
                    Match.kickoff_at >= now - RECENT_WINDOW,
                    Match.kickoff_at <= now + timedelta(days=prediction_days_ahead(db)))
             .order_by(Match.kickoff_at))
    return list(db.scalars(query))


def predictions_by_match(db: Session, user: User | None, match_ids: list[int]) -> dict:
    if user is None or not match_ids:
        return {}
    query = select(Prediction).where(Prediction.user_id == user.id,
                                     Prediction.match_id.in_(match_ids))
    return {p.match_id: p for p in db.scalars(query)}


def probabilities_by_match(db: Session, matches: list[Match]) -> dict:
    """{match_id: Probabilities} ; les matchs sans pourcentages sont absents.

    Une seule requête pour les pronostics des matchs sans pourcentages du fournisseur.
    """
    without_provider = [m.id for m in matches if m.prob_home is None]
    scores: dict[int, list[tuple[int, int]]] = {}
    if without_provider:
        rows = db.execute(select(Prediction.match_id, Prediction.home_score, Prediction.away_score)
                          .where(Prediction.match_id.in_(without_provider)))
        for match_id, home, away in rows:
            scores.setdefault(match_id, []).append((home, away))
    result = {}
    for m in matches:
        probabilities = match_probabilities(m.prob_home, m.prob_draw, m.prob_away,
                                            scores.get(m.id, []))
        if probabilities:
            result[m.id] = probabilities
    return result


def match_context(request: Request, db: Session, user: User | None, matches: list[Match],
                  now: datetime) -> dict:
    """Données communes aux pages qui affichent des cartes de match."""
    tz = resolve_timezone(request.cookies.get("tz"))
    return {
        "user": user,
        "now": now,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "predictions": predictions_by_match(db, user, [m.id for m in matches]),
        "probabilities": probabilities_by_match(db, matches),
        "open_ids": {m.id for m in matches if is_prediction_open(m.status, m.kickoff_at, now)},
    }


# --- Pages ---

@router.get("/matches")
def matches_page(request: Request, db: Session = Depends(get_db),
                 user: User | None = Depends(current_user)):
    now = utc_now()
    matches = upcoming_matches(db, now)
    context = match_context(request, db, user, matches, now)
    context["days"] = group_by_day_and_competition(matches, context["tz"])
    context["to_predict"] = sum(1 for m_id in context["open_ids"] if m_id not in context["predictions"])
    return templates.TemplateResponse(request, "matches.html", context)


@router.post("/matches/{match_id}/prediction")
def save_one_prediction(match_id: int, db: Session = Depends(get_db),
                        user: User = Depends(require_user),
                        home: str = Form(""), away: str = Form("")):
    """Enregistrement automatique d'un pronostic, envoyé par predictions.js dès que
    les deux cases d'un match sont remplies. Réponse en JSON."""
    error = save_prediction(db, user.id, match_id, home, away, utc_now())
    if error:
        status = 404 if error == "error_match_not_found" else 400
        return JSONResponse({"saved": False, "error": translate(error)}, status_code=status)
    return {"saved": True}


def matches_to_predict(db: Session, user: User, now: datetime) -> list[Match]:
    """Matchs encore ouverts sur lesquels le joueur n'a pas de pronostic, du plus proche au plus lointain."""
    open_matches = [m for m in upcoming_matches(db, now)
                    if is_prediction_open(m.status, m.kickoff_at, now)]
    predicted = predictions_by_match(db, user, [m.id for m in open_matches])
    return [m for m in open_matches if m.id not in predicted]


def prediction_history(db: Session, user: User) -> list[Prediction]:
    query = (select(Prediction).join(Prediction.match)
             .options(joinedload(Prediction.match).joinedload(Match.competition))
             .where(Prediction.user_id == user.id)
             .order_by(Match.kickoff_at.desc()).limit(HISTORY_LIMIT))
    return list(db.scalars(query))
