"""Back-office (SPEC §9), réservé aux joueurs avec `is_admin` (scripts/make_admin.py)."""
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_admin
from app.db import get_db
from app.jobs.import_competitions import import_competitions
from app.jobs.score_predictions import rescore_corrected_match
from app.jobs.sync import Task, run_sync
from app.models import Competition, Match, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.providers import make_provider
from app.providers.base import ProviderError
from app.routes.accounts import redirect
from app.routes.internal import get_provider_factory
from app.services.admin_matches import STATUSES, parse_correction, parse_new_match
from app.services import kpi_store
from app.services.game_settings import parse_settings
from app.services.settings_store import current_rules, get_settings, save_settings
from app.services.timezones import resolve_timezone
from app.templating import templates

MATCHES_WINDOW = timedelta(days=7)  # liste des matchs : 7 jours avant et après aujourd'hui

router = APIRouter(prefix="/admin")


@router.get("")
def admin_home(request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_admin)):
    """Accueil du back-office : KPIs, puis liens vers les autres pages."""
    now = utc_now()
    context = {"user": user, "totals": kpi_store.totals(db, now),
               "weeks": kpi_store.weekly(db, now.date()),
               "tz": resolve_timezone(request.cookies.get("tz"))}
    return templates.TemplateResponse(request, "admin/index.html", context)


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_admin)):
    rescored = request.query_params.get("rescored")
    context = {"user": user, "settings": get_settings(db), "form": None, "error": None,
               "saved": request.query_params.get("saved"),
               "rescored": int(rescored) if rescored and rescored.isdigit() else None}
    return templates.TemplateResponse(request, "admin/settings.html", context)


@router.post("/settings")
def settings_submit(request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_admin), winner_points: str = Form(""),
                    exact_bonus: str = Form(""), league_max_members: str = Form(""),
                    prediction_days_ahead: str = Form("")):
    settings, error = parse_settings(winner_points, exact_bonus, league_max_members,
                                     prediction_days_ahead)
    if error:
        form = {"winner_points": winner_points, "exact_bonus": exact_bonus,
                "league_max_members": league_max_members,
                "prediction_days_ahead": prediction_days_ahead}
        context = {"user": user, "settings": get_settings(db), "form": form, "error": error,
                   "saved": None, "rescored": None}
        return templates.TemplateResponse(request, "admin/settings.html", context,
                                          status_code=400)
    rescored = save_settings(db, settings, utc_now())
    return redirect(f"/admin/settings?saved=1&rescored={rescored}" if rescored
                    else "/admin/settings?saved=1")


# --- Compétitions ---

@router.get("/competitions")
def competitions_page(request: Request, db: Session = Depends(get_db),
                      user: User = Depends(require_admin)):
    return render_competitions(request, db, user, notice=request.query_params.get("notice"))


def render_competitions(request: Request, db: Session, user: User, notice: str | None = None,
                        error: str | None = None, status_code: int = 200):
    competitions = db.scalars(select(Competition).order_by(
        Competition.is_active.desc(), Competition.provider, Competition.name)).all()
    context = {"user": user, "competitions": competitions, "notice": notice, "error": error}
    return templates.TemplateResponse(request, "admin/competitions.html", context,
                                      status_code=status_code)


@router.post("/competitions/{competition_id}/toggle")
def toggle_competition(competition_id: int, db: Session = Depends(get_db),
                       user: User = Depends(require_admin)):
    competition = db.get(Competition, competition_id) or _not_found()
    competition.is_active = not competition.is_active
    db.commit()
    return redirect("/admin/competitions")


@router.post("/competitions/refresh")
def refresh_competitions(request: Request, db: Session = Depends(get_db),
                         user: User = Depends(require_admin)):
    """Liste des compétitions du fournisseur (1 appel chez football-data.org)."""
    try:
        import_competitions(db, make_provider(db))
    except ProviderError as exc:
        db.rollback()
        return render_competitions(request, db, user, error=str(exc), status_code=502)
    return redirect("/admin/competitions?notice=admin_competitions_refreshed")


# --- Matchs ---

@router.get("/matches")
def matches_page(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_admin)):
    now = utc_now()
    matches = db.scalars(select(Match).options(joinedload(Match.competition))
                         .where(Match.kickoff_at >= now - MATCHES_WINDOW,
                                Match.kickoff_at <= now + MATCHES_WINDOW)
                         .order_by(Match.kickoff_at)).all()
    query = request.query_params
    synced = query.get("synced")
    context = {"user": user, "matches": matches, "tz": resolve_timezone(request.cookies.get("tz")),
               "notice": query.get("notice"), "sync_task": query.get("task"),
               "synced": int(synced) if synced and synced.isdigit() else None,
               "sync_error": query.get("error")}
    return templates.TemplateResponse(request, "admin/matches.html", context)


@router.post("/matches/sync/{task}")
def sync_matches(task: Task, db: Session = Depends(get_db), user: User = Depends(require_admin),
                 provider_factory=Depends(get_provider_factory)):
    """Même synchronisation que la GitHub Action, lancée à la main depuis le back-office."""
    result = run_sync(db, provider_factory, task, utc_now())
    if "error" in result:
        return redirect(f"/admin/matches?{urlencode({'task': task, 'error': result['error']})}")
    return redirect(f"/admin/matches?task={task}&synced={result['matches']}")


@router.get("/matches/new")
def new_match_page(request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_admin)):
    return render_new_match(request, db, user)


def render_new_match(request: Request, db: Session, user: User, form: dict | None = None,
                     error: str | None = None, status_code: int = 200):
    competitions = db.scalars(select(Competition).where(Competition.is_active.is_(True))
                              .order_by(Competition.name)).all()
    context = {"user": user, "competitions": competitions, "form": form or {}, "error": error}
    return templates.TemplateResponse(request, "admin/match_new.html", context,
                                      status_code=status_code)


@router.post("/matches/new")
def new_match_submit(request: Request, db: Session = Depends(get_db),
                     user: User = Depends(require_admin), competition_id: str = Form(""),
                     home_team: str = Form(""), away_team: str = Form(""),
                     day: str = Form(""), hour: str = Form("")):
    form = {"competition_id": competition_id, "home_team": home_team, "away_team": away_team,
            "day": day, "hour": hour}
    competition = db.get(Competition, int(competition_id)) if competition_id.isdigit() else None
    fields, error = parse_new_match(home_team, away_team, day, hour,
                                    resolve_timezone(request.cookies.get("tz")))
    if competition is None:
        error = "error_competition"
    if error:
        return render_new_match(request, db, user, form, error, status_code=400)
    # Sans fournisseur ni identifiant : la synchro ne le touchera jamais
    db.add(Match(competition=competition, status=MatchStatus.SCHEDULED, **fields))
    db.commit()
    return redirect("/admin/matches?notice=admin_match_added")


@router.get("/matches/{match_id}")
def match_page(match_id: int, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_admin)):
    return render_match(request, db, user, db.get(Match, match_id) or _not_found())


def render_match(request: Request, db: Session, user: User, match: Match,
                 form: dict | None = None, error: str | None = None, status_code: int = 200):
    context = {"user": user, "match": match, "statuses": STATUSES, "error": error,
               "tz": resolve_timezone(request.cookies.get("tz")), "form": form or {
                   "status": match.status,
                   "home_score": "" if match.home_score is None else match.home_score,
                   "away_score": "" if match.away_score is None else match.away_score}}
    return templates.TemplateResponse(request, "admin/match.html", context,
                                      status_code=status_code)


@router.post("/matches/{match_id}")
def correct_match(match_id: int, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_admin), status: str = Form(""),
                  home_score: str = Form(""), away_score: str = Form("")):
    match = db.get(Match, match_id) or _not_found()
    fields, error = parse_correction(status, home_score, away_score)
    if error:
        form = {"status": status, "home_score": home_score, "away_score": away_score}
        return render_match(request, db, user, match, form, error, status_code=400)
    for name, value in fields.items():
        setattr(match, name, value)
    match.score_locked = True  # la synchro ne doit pas écraser la correction
    db.commit()
    rescore_corrected_match(db, match, current_rules(db), utc_now())
    return redirect("/admin/matches?notice=admin_match_corrected")


@router.post("/matches/{match_id}/unlock")
def unlock_match(match_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_admin)):
    match = db.get(Match, match_id) or _not_found()
    match.score_locked = False
    db.commit()
    return redirect(f"/admin/matches/{match.id}")


def _not_found():
    raise HTTPException(404)
