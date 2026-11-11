"""Liste des matchs, saisie des pronostics, historique du joueur."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.i18n import translate
from app.models import Competition, Match, Prediction, User
from app.models.types import utc_now
from app.services.deadlines import is_prediction_open
from app.services.match_days import (calendar_days, calendar_end, day_prediction_status, match_day,
                                     pick_day)
from app.services.match_filters import (ALL_COMPETITIONS, competition_code, competition_keys,
                                        is_mine, is_todo, matches_status, parse_status)
from app.services.predictions import save_prediction
from app.services.probabilities import player_trends
from app.services.settings_store import prediction_days_ahead
from app.services.timezones import local_day, resolve_timezone
from app.templating import templates

router = APIRouter()

RECENT_WINDOW = timedelta(hours=3)  # garde visibles les matchs en cours ou juste finis
HISTORY_LIMIT = 50


# --- Lectures en base ---

def upcoming_matches(db: Session, now: datetime, until: datetime | None = None) -> list[Match]:
    """Matchs des compétitions actives, des 3 dernières heures aux N prochains jours (réglage admin).

    `until` : fin de la période (la page Pronos s'arrête à la fin du dernier jour de son calendrier).
    """
    until = until or now + timedelta(days=prediction_days_ahead(db))
    query = (select(Match).join(Match.competition).options(joinedload(Match.competition))
             .where(Competition.is_active.is_(True),
                    Match.kickoff_at >= now - RECENT_WINDOW,
                    Match.kickoff_at < until)
             .order_by(Match.kickoff_at))
    return list(db.scalars(query))


def predictions_by_match(db: Session, user: User, match_ids: list[int]) -> dict:
    if not match_ids:
        return {}
    query = select(Prediction).where(Prediction.user_id == user.id,
                                     Prediction.match_id.in_(match_ids))
    return {p.match_id: p for p in db.scalars(query)}


def trends_by_match(db: Session, match_ids: set[int]) -> dict:
    """{match_id: Probabilities} : tendance 1 / N / 2 des pronostics de tous les joueurs.

    Une seule requête ; les matchs sous le seuil de pronostics sont absents.
    """
    scores: dict[int, list[tuple[int, int]]] = {}
    if match_ids:
        rows = db.execute(select(Prediction.match_id, Prediction.home_score, Prediction.away_score)
                          .where(Prediction.match_id.in_(match_ids)))
        for match_id, home, away in rows:
            scores.setdefault(match_id, []).append((home, away))
    trends = {match_id: player_trends(items) for match_id, items in scores.items()}
    return {match_id: trend for match_id, trend in trends.items() if trend}


def match_context(request: Request, db: Session, user: User, matches: list[Match],
                  now: datetime) -> dict:
    """Données communes aux pages qui affichent des cartes de match."""
    tz = resolve_timezone(request.cookies.get("tz"))
    open_ids = {m.id for m in matches if is_prediction_open(m.status, m.kickoff_at, now)}
    return {
        "user": user,
        "now": now,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "predictions": predictions_by_match(db, user, [m.id for m in matches]),
        "trends": trends_by_match(db, open_ids),  # seulement les matchs encore ouverts
        "open_ids": open_ids,
    }


def competition_pills(matches: list[Match]) -> list[dict]:
    """Une pastille par compétition présente dans les matchs, par ordre alphabétique."""
    competitions = sorted({m.competition for m in matches}, key=lambda c: c.name)
    codes = {c.id: competition_code(c.external_id, c.name) for c in competitions}
    keys = competition_keys(list(codes.items()))
    return [{"key": keys[c.id], "id": c.id, "name": c.name, "code": codes[c.id],
             "logo_url": c.logo_url} for c in competitions]


def filter_context(matches: list[Match], context: dict, comp: str | None,
                   status: str | None, day_keys: dict[int, str] | None = None,
                   day: str | None = None) -> dict:
    """Filtres de la page Pronos, appliqués dès l'affichage (la page reste juste sans JavaScript).

    Avec `day` : seuls les matchs de ce jour du calendrier (`day_keys` : {match_id: "2026-11-12"})
    sont visibles et comptés dans les pastilles.
    """
    pills = competition_pills(matches)
    comp_keys = {p["id"]: p["key"] for p in pills}
    comp = comp if comp in comp_keys.values() else ALL_COMPETITIONS
    status = parse_status(status)
    counts = {p["key"]: 0 for p in pills} | {ALL_COMPETITIONS: 0}
    visible_ids = set()
    for m in matches:
        if day is not None and day_keys[m.id] != day:
            continue
        has_prediction = m.id in context["predictions"]
        if not matches_status(status, is_todo(m.id in context["open_ids"], has_prediction),
                              is_mine(m.status, has_prediction)):
            continue
        key = comp_keys[m.competition_id]
        counts[key] += 1
        counts[ALL_COMPETITIONS] += 1
        if comp in (ALL_COMPETITIONS, key):
            visible_ids.add(m.id)
    return {"pills": pills, "comp_keys": comp_keys, "comp": comp, "status": status,
            "counts": counts, "visible_ids": visible_ids}


# --- Pages ---

@router.get("/matches")
def matches_page(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user),
                 comp: str | None = None, status: str | None = None, day: str | None = None):
    """Page Pronos : calendrier des N jours ouverts, matchs du jour choisi,
    filtres ?day=2026-11-12&comp=<clé>&status=todo|mine|all."""
    now = utc_now()
    tz = resolve_timezone(request.cookies.get("tz"))
    today = local_day(now, tz)
    days = calendar_days(today, prediction_days_ahead(db))
    selected = pick_day(day, days)
    matches = upcoming_matches(db, now, until=calendar_end(days, tz))
    context = match_context(request, db, user, matches, now)
    day_keys = {m.id: match_day(m.kickoff_at, tz, today).isoformat() for m in matches}
    context |= filter_context(matches, context, comp, status, day_keys, selected.isoformat())
    # Tous les jours du calendrier, même sans match ; seul le jour choisi est affiché
    context["days"] = [(d, [m for m in matches if day_keys[m.id] == d.isoformat()]) for d in days]
    context["selected_day"] = selected
    # Rond sous chaque jour du calendrier : tous les matchs du jour, sans les filtres
    # (pronos déjà chargés en une requête par match_context)
    context["day_status"] = {d: day_prediction_status(ms, context["predictions"], now)
                             for d, ms in context["days"]}
    context["to_predict"] = sum(1 for m_id in context["open_ids"] if m_id not in context["predictions"])
    return templates.TemplateResponse(request, "matches.html", context)


@router.post("/matches/{match_id}/prediction")
def save_one_prediction(match_id: int, db: Session = Depends(get_db),
                        user: User = Depends(require_user),
                        home: str = Form(""), away: str = Form("")):
    """Enregistrement d'un pronostic, envoyé par predictions.js (bouton « Valider »).
    Réponse en JSON ; un match fermé entre-temps est refusé avec son message."""
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
