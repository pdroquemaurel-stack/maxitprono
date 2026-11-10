"""Page d'accueil (« Ma ligue »), règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.leagues import share_links
from app.routes.matches import matches_to_predict, upcoming_matches
from app.services import league_store
from app.services.deadlines import is_prediction_open
from app.services.home import featured_competition
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
        return guest_home(request, db)
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
        context.update(share_links(request, league, user))
    response = templates.TemplateResponse(request, "home.html", context)
    if league and request.query_params.get("league"):
        response.set_cookie(LEAGUE_COOKIE, str(league.id), max_age=LEAGUE_COOKIE_AGE,
                            httponly=True, samesite="lax")
    return response


def guest_home(request: Request, db: Session):
    """Accueil du visiteur : présentation, 3 prochains matchs, compétition du moment."""
    now = utc_now()
    open_matches = [m for m in upcoming_matches(db, now)
                    if is_prediction_open(m.status, m.kickoff_at, now)]
    rules = current_rules(db)
    tz = resolve_timezone(request.cookies.get("tz"))
    return templates.TemplateResponse(request, "home_guest.html", {
        "user": None,
        "now": now,
        "tz": tz,
        "today": now.astimezone(tz).date(),
        "next_matches": open_matches[:3],
        "featured": featured_competition(open_matches, now),
        "exact_points": rules.winner_points + rules.exact_bonus,
        "good_points": rules.winner_points,
    })


@router.get("/rules")
def rules(request: Request, db: Session = Depends(get_db),
          user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html",
                                      {"user": user, "rules": current_rules(db)})


# Pages du pied de page pas encore rédigées
COMING_SOON_PAGES = {"/help": "footer_help", "/privacy": "footer_privacy", "/legal": "footer_legal"}


def coming_soon(request: Request, user: User | None = Depends(current_user)):
    title_key = COMING_SOON_PAGES[request.url.path]
    return templates.TemplateResponse(request, "coming_soon.html",
                                      {"user": user, "title_key": title_key})


for _path in COMING_SOON_PAGES:
    router.add_api_route(_path, coming_soon, methods=["GET"])


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
