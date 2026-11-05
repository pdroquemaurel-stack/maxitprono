"""Page des classements : ligue, général, par pays, par compétition, par semaine."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.i18n.countries import COUNTRY_CODES, PILOT_COUNTRIES
from app.models import Competition, User
from app.services import league_store
from app.models.types import utc_now
from app.services.leaderboards import leaderboard
from app.services.leagues import pick_league
from app.services.ranking import find_player, week_bounds, week_start
from app.templating import templates

router = APIRouter()

TABS = ("league", "general", "country", "competition", "week")
TOP_COUNT = 50


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    return int(value) if value and value.isdigit() else None


@router.get("/leaderboard")
def leaderboard_page(request: Request, db: Session = Depends(get_db),
                     user: User | None = Depends(current_user)):
    params = request.query_params
    leagues = league_store.my_leagues(db, user.id) if user else []
    # Onglet par défaut : la ligue si le joueur en a une (la ligue est au centre du jeu)
    default_tab = "league" if leagues else "general"
    tab = params.get("tab") if params.get("tab") in TABS else default_tab
    context = {"user": user, "tab": tab, "tabs": TABS}

    if tab == "league":
        wanted = params.get("league") or request.cookies.get("league")
        league_id = pick_league([league.id for league, _ in leagues], wanted)
        context.update(leagues=leagues, league_id=league_id)
        ranking = leaderboard(db, league_id=league_id) if league_id else []
    elif tab == "country":
        country = params.get("country", "")
        if country not in COUNTRY_CODES:
            country = user.country_code if user else PILOT_COUNTRIES[0]
        context["country"] = country
        ranking = leaderboard(db, country_code=country)
    elif tab == "competition":
        competitions = list(db.scalars(select(Competition).where(Competition.is_active.is_(True))
                                       .order_by(Competition.name)))
        ids = {c.id for c in competitions}
        wanted = _parse_int(params.get("competition"))
        selected = wanted if wanted in ids else (competitions[0].id if competitions else None)
        context.update(competitions=competitions, competition_id=selected)
        ranking = leaderboard(db, competition_id=selected) if selected else []
    elif tab == "week":
        monday = week_start(_parse_date(params.get("week")) or utc_now().date())
        context.update(week=monday, previous_week=monday - timedelta(days=7),
                       next_week=monday + timedelta(days=7), week_end=monday + timedelta(days=6))
        ranking = leaderboard(db, period=week_bounds(monday))
    else:
        ranking = leaderboard(db)

    me = find_player(ranking, user.id) if user else None
    context.update(top=ranking[:TOP_COUNT], me=me, total=len(ranking),
                   me_outside_top=me is not None and me.rank > TOP_COUNT)
    return templates.TemplateResponse(request, "leaderboard.html", context)
