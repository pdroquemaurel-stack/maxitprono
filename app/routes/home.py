"""Page d'accueil (« Ma ligue »), règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.leagues import share_links
from app.routes.matches import matches_to_predict
from app.services import league_store
from app.services.leaderboards import leaderboard
from app.services.leagues import pick_league
from app.services.settings_store import current_rules
from app.services.ranking import find_player
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()

LEAGUE_COOKIE = "league"  # dernière ligue choisie dans le sélecteur
LEAGUE_COOKIE_AGE = 365 * 24 * 3600


@router.get("/")
def home(request: Request, db: Session = Depends(get_db),
         user: User | None = Depends(current_user)):
    if user is None:
        return templates.TemplateResponse(request, "home.html", {"user": None})
    now = utc_now()
    leagues = league_store.my_leagues(db, user.id)
    wanted = request.query_params.get("league") or request.cookies.get(LEAGUE_COOKIE)
    league_id = pick_league([league.id for league, _ in leagues], wanted)
    league, members = next(((l, n) for l, n in leagues if l.id == league_id), (None, 0))

    # Classement de la ligue choisie, sinon classement général : suffisant pour le POC
    ranking = leaderboard(db, league_id=league.id) if league else leaderboard(db)
    context = {
        "user": user,
        "now": now,
        "tz": resolve_timezone(request.cookies.get("tz")),
        "to_predict": matches_to_predict(db, user, now),
        "podium": ranking[:3],
        "me": find_player(ranking, user.id),
        "total": len(ranking),
        "leagues": leagues,
        "league": league,
        "player_count": members if league else len(ranking),
        "activity": league_store.recent_activity(db, league, now) if league else [],
    }
    if league:
        context.update(share_links(request, league))
    response = templates.TemplateResponse(request, "home.html", context)
    if league and request.query_params.get("league"):
        response.set_cookie(LEAGUE_COOKIE, str(league.id), max_age=LEAGUE_COOKIE_AGE,
                            httponly=True, samesite="lax")
    return response


@router.get("/rules")
def rules(request: Request, db: Session = Depends(get_db),
          user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html",
                                      {"user": user, "rules": current_rules(db)})


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
