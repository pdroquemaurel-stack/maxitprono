"""Liste des matchs, saisie des pronostics, historique du joueur."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
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
HISTORY_LIMIT = 50


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
        "now": now,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "predictions": predictions_by_match(db, user, [m.id for m in matches]),
        "open_ids": {m.id for m in matches if is_prediction_open(m.status, m.kickoff_at, now)},
        "saved_count": _int_or_none(request.query_params.get("saved")),
        "entered": {},  # valeurs saisies, réaffichées en cas d'erreur
        "errors": {},  # {match_id: clé d'erreur}
    }


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


def submitted_scores(form) -> dict[int, tuple[str, str]]:
    """{match_id: (domicile, extérieur)} lus dans les champs home_<id> et away_<id>."""
    scores = {}
    for key in form.keys():
        if key.startswith("home_") and key[5:].isdigit():
            match_id = int(key[5:])
            scores[match_id] = (form.get(key, ""), form.get(f"away_{match_id}", ""))
    return scores


# --- Pages ---

@router.get("/matches")
def matches_page(request: Request, db: Session = Depends(get_db),
                 user: User | None = Depends(current_user)):
    return render_matches(request, db, user)


def render_matches(request: Request, db: Session, user: User | None,
                   entered: dict | None = None, errors: dict | None = None,
                   saved_count: int | None = None):
    now = utc_now()
    matches = upcoming_matches(db, now)
    context = match_context(request, db, user, matches, now)
    context["days"] = group_by_day_and_competition(matches, context["tz"])
    context["to_predict"] = sum(1 for m_id in context["open_ids"] if m_id not in context["predictions"])
    context["entered"], context["errors"] = entered or {}, errors or {}
    if saved_count:
        context["saved_count"] = saved_count
    return templates.TemplateResponse(request, "matches.html", context)


@router.post("/matches/predictions")
async def submit_predictions(request: Request, db: Session = Depends(get_db),
                             user: User = Depends(require_user)):
    """Enregistre en une fois tous les pronostics saisis dans la liste."""
    entered = submitted_scores(await request.form())
    now = utc_now()
    saved, errors = 0, {}
    for match_id, (home, away) in entered.items():
        if not home.strip() and not away.strip():
            continue  # match laissé vide : rien à faire
        error = save_prediction(db, user.id, match_id, home, away, now)
        if error:
            errors[match_id] = error
        else:
            saved += 1
    if errors:
        return render_matches(request, db, user, entered, errors, saved)
    return RedirectResponse(f"/matches?saved={saved}", status_code=303)


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
