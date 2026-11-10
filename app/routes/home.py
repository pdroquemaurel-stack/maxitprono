"""Page d'accueil (visiteur et joueur), règles du jeu, pages à venir et vérification de santé."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import current_user
from app.db import get_db
from app.models import Match, Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.routes.leagues import LEAGUE_COOKIE, LEAGUE_COOKIE_AGE, league_card
from app.routes.matches import match_context, upcoming_matches
from app.routes.profile import badges_context
from app.services import league_store, profile_store, rank_history
from app.services import profile_stats as stats
from app.services.activity import friends_feed
from app.services.deadlines import is_prediction_open
from app.services.home import (badge_progress, featured_competition, local_day_bounds,
                               places_gained)
from app.services.leagues import pick_league
from app.services.settings_store import current_rules
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()

HOME_TODO_LIMIT = 3  # matchs à pronostiquer affichés sur l'accueil


@router.get("/")
def home(request: Request, db: Session = Depends(get_db),
         user: User | None = Depends(current_user)):
    if user is None:
        return guest_home(request, db)
    now = utc_now()
    tz = resolve_timezone(request.cookies.get("tz"))
    leagues = league_store.my_leagues(db, user.id)
    wanted = request.query_params.get("league") or request.cookies.get(LEAGUE_COOKIE)
    main_id = pick_league([league.id for league, _ in leagues], wanted)
    cards = [league_card(db, league, count, user, now) for league, count in leagues]
    main_card = next((card for card in cards if card["league"].id == main_id), None)

    # Pronos à faire : matchs ouverts sans prono, les plus proches d'abord
    open_matches = [m for m in upcoming_matches(db, now)
                    if is_prediction_open(m.status, m.kickoff_at, now)]
    context = match_context(request, db, user, open_matches, now)
    to_predict = [m for m in open_matches if m.id not in context["predictions"]]

    # Hier (jour du fuseau du joueur) : résultats, points, places gagnées
    yesterday = context["today"] - timedelta(days=1)
    results = yesterday_results(db, user, *local_day_bounds(yesterday, tz))
    all_picks = profile_store.played_picks(db, user.id)
    outcomes = stats.chronological_outcomes(all_picks)
    badges = badges_context(db, user, all_picks)
    next_badge = badges["next_badge"]

    context.update({
        "to_predict": to_predict,
        "to_predict_count": len(to_predict),
        "todo_matches": to_predict[:HOME_TODO_LIMIT],
        "next_match": open_matches[0] if open_matches else None,
        "results": results,
        "yesterday_points": sum(p.points or 0 for p in results),
        "yesterday_places": places_gained(rank_history.player_ranks(db, user.id), yesterday),
        "exact_result": next((p for p in results if p.is_exact), None),
        "summary": stats.summarize(all_picks),
        "current_streak": stats.current_streak(outcomes),
        "cards": cards,
        "main_card": main_card,
        "feed": friends_feed([event for card in cards for event in card["activity_all"]], user.id),
        "next_badge": next_badge,
        "badge_progress": badge_progress(next_badge, stats.BADGE_GOALS) if next_badge else None,
    })
    response = templates.TemplateResponse(request, "home_player.html", context)
    if main_card and request.query_params.get("league"):
        response.set_cookie(LEAGUE_COOKIE, str(main_id), max_age=LEAGUE_COOKIE_AGE,
                            httponly=True, samesite="lax")
    return response


def yesterday_results(db: Session, user: User, start, end) -> list[Prediction]:
    """Mes pronos comptés sur les matchs terminés entre `start` et `end` (UTC)."""
    query = (select(Prediction).join(Prediction.match)
             .options(joinedload(Prediction.match))
             .where(Prediction.user_id == user.id, Prediction.points.is_not(None),
                    Match.status == MatchStatus.FINISHED,
                    Match.kickoff_at >= start, Match.kickoff_at < end)
             .order_by(Match.kickoff_at))
    return list(db.scalars(query))


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
