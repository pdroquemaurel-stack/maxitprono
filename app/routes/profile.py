"""Page Profil (statistiques), modification du profil et historique des pronostics."""
from datetime import UTC, datetime, time

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.i18n.countries import COUNTRY_CODES
from app.models import Competition, User
from app.models.types import utc_now
from app.routes.accounts import read_avatar
from app.routes.leagues import share_links
from app.routes.matches import prediction_history
from app.services import league_store, profile_store
from app.services import profile_stats as stats
from app.services.accounts import nickname_key, validate_country, validate_nickname
from app.services.leaderboards import leaderboard
from app.services.leagues import pick_league
from app.services.ranking import find_player, week_bounds, week_start
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()

PERIODS = ("season", "week", "competition")
SEASON_START = datetime(2000, 1, 1, tzinfo=UTC)  # « Saison » : tous les matchs joués


# --- Page Profil ---

@router.get("/profile")
def profile(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    params = request.query_params
    period = params.get("period") if params.get("period") in PERIODS else "season"
    all_picks = profile_store.played_picks(db, user.id)
    context = {"user": user, "period": period, "periods": PERIODS}

    # Filtre de période : pronos pris en compte et filtres des classements
    start, end, competition_id = SEASON_START, None, None
    if period == "week":
        monday = week_start(utc_now().date())
        start, end = week_bounds(monday)
        context["week"] = monday
    elif period == "competition":
        competitions = list(db.execute(select(Competition.id, Competition.name)
                                       .where(Competition.is_active.is_(True))
                                       .order_by(Competition.name)))
        competition_id = stats.choose_competition(competitions, params.get("competition"))
        context.update(competitions=competitions, competition_id=competition_id,
                       competition_name=dict(competitions).get(competition_id, ""))
    picks = [pick for pick in all_picks if pick.kickoff_at >= start
             and (end is None or pick.kickoff_at < end)
             and (competition_id is None or pick.competition_id == competition_id)]
    outcomes = stats.chronological_outcomes(picks)
    competition_stats = stats.by_competition(picks)
    if period == "week":
        context["matchday"] = stats.single_matchday(picks)
    context.update(
        summary=stats.summarize(picks),
        form=stats.recent_form(outcomes),
        current_streak=stats.current_streak(outcomes),
        best_streak=stats.best_streak(outcomes),
        competition_stats=competition_stats,
        strongest=stats.strongest_competition(competition_stats),
    )
    if period != "competition" or competition_id:
        context.update(rankings(request, db, user, picks, start, end, competition_id))
    context.update(badges_context(db, user, all_picks))
    context["share_stats_url"] = context.get("join_url") or str(request.base_url)
    return templates.TemplateResponse(request, "profile.html", context)


def rankings(request: Request, db: Session, user: User, picks: list[stats.PlayedPick],
             start: datetime, end: datetime | None, competition_id: int | None) -> dict:
    """Mes rangs (ligue, pays, général) sur la période, et l'évolution dans ma ligue."""
    filters = {"competition_id": competition_id, "period": (start, end) if end else None}
    leagues = league_store.my_leagues(db, user.id)
    league_id = pick_league([league.id for league, _ in leagues], request.cookies.get("league"))
    league, members = next(((l, n) for l, n in leagues if l.id == league_id), (None, 0))
    country = leaderboard(db, country_code=user.country_code, **filters)
    general = leaderboard(db, **filters)
    context = {"league": league, "league_members": members,
               "country_rank": find_player(country, user.id), "country_total": len(country),
               "general_rank": find_player(general, user.id), "general_total": len(general)}
    if league:
        now = find_player(leaderboard(db, league_id=league.id, **filters), user.id)
        context.update(league_rank=now, league_change=league_change(db, league.id, user.id, now,
                                                                    picks, start, competition_id))
        context.update(share_links(request, league))
    return context


def league_change(db: Session, league_id: int, user_id: int, now, picks, start: datetime,
                  competition_id: int | None) -> int | None:
    """Places gagnées dans la ligue lors de ma dernière journée jouée."""
    if not picks:
        return None
    last_day = max(pick.kickoff_at for pick in picks).date()
    before_end = datetime.combine(last_day, time.min, tzinfo=UTC)
    before = leaderboard(db, league_id=league_id, competition_id=competition_id,
                         period=(start, before_end))
    return stats.rank_change(find_player(before, user_id), now)


def badges_context(db: Session, user: User, all_picks: list[stats.PlayedPick]) -> dict:
    """Badges sur toute la carrière du joueur (pas filtrés par la période)."""
    badges = stats.compute_badges(
        exacts=stats.summarize(all_picks).exacts,
        best_climb=stats.best_daily_climb(profile_store.daily_scores(db), user.id),
        invited_friends=profile_store.invited_friends(db, user.id),
        best_success_streak=stats.best_streak(stats.chronological_outcomes(all_picks)),
    )
    return {"badges": badges, "next_badge": stats.next_badge(badges),
            "badges_unlocked": sum(badge.unlocked for badge in badges)}


# --- Modifier mon profil ---

@router.get("/profile/edit")
def profile_edit(request: Request, user: User = Depends(require_user)):
    return render_edit(request, user)


def render_edit(request: Request, user: User, error: str | None = None,
                form: dict | None = None, status_code: int = 200):
    form = form or {"nickname": user.nickname, "country_code": user.country_code}
    return templates.TemplateResponse(request, "profile_edit.html",
                                      {"user": user, "error": error, "form": form},
                                      status_code=status_code)


@router.post("/profile")
def profile_submit(request: Request, db: Session = Depends(get_db),
                   user: User = Depends(require_user), nickname: str = Form(""),
                   country_code: str = Form(""), avatar_data: str = Form(""),
                   avatar_file: UploadFile | None = File(None)):
    nickname = nickname.strip() or user.nickname  # pseudo absent du formulaire : inchangé
    avatar, mime, error = read_avatar(avatar_data, avatar_file)
    error = (error or validate_nickname(nickname)
             or validate_country(country_code, COUNTRY_CODES))
    if error is None and profile_store.nickname_taken(db, nickname_key(nickname), user.id):
        error = "error_nickname_taken"
    if error:
        db.rollback()
        return render_edit(request, user, error,
                           {"nickname": nickname, "country_code": country_code}, 400)
    user.nickname, user.nickname_key = nickname, nickname_key(nickname)
    user.country_code = country_code
    if avatar:
        user.avatar, user.avatar_mime = avatar, mime
    try:
        db.commit()
    except IntegrityError:  # même pseudo pris au même instant par un autre joueur
        db.rollback()
        return render_edit(request, db.get(User, user.id), "error_nickname_taken",
                           {"nickname": nickname, "country_code": country_code}, 400)
    return RedirectResponse("/profile/edit?saved=1", status_code=303)


# --- Historique ---

@router.get("/profile/history")
def profile_history(request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_user)):
    return templates.TemplateResponse(request, "profile_history.html",
                                      {"user": user, "history": prediction_history(db, user),
                                       "tz": resolve_timezone(request.cookies.get("tz"))})
