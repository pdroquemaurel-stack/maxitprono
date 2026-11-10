"""Ligues privées : mes ligues, création, détail, réglages, invitation par code ou par lien.

Rejoindre une ligue passe toujours par un POST (formulaire, connexion ou inscription) :
WhatsApp et les réseaux sociaux ouvrent les liens partagés pour en faire un aperçu,
un GET ne doit rien changer.
"""
from dataclasses import replace
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import current_user, require_user
from app.db import get_db
from app.i18n import translate
from app.models import League, User
from app.models.types import utc_now
from app.routes.accounts import redirect
from app.routes.matches import matches_to_predict
from app.services import league_store
from app.services.deadlines import prediction_deadline
from app.services.leagues import (LEAGUE_COLORS, clean_competition_ids, gap_to_leader,
                                  league_trend, ranking_preview, sort_league_predictions,
                                  standings, week_extremes)
from app.services.ranking import find_player
from app.services.settings_store import current_rules, league_max_members
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()

DONE_MESSAGES = {"left": "league_left", "deleted": "league_deleted"}
TABS = ("ranking", "matches")
PREVIEW_ROWS = 7  # lignes sous le podium avant « Voir les N membres »
CARD_FACES = 3  # avatars empilés sur la carte d'une ligue
LEAGUE_COOKIE = "league"  # ligue principale : la dernière ouverte (ou choisie par ?league=)
LEAGUE_COOKIE_AGE = 365 * 24 * 3600


def member_league(db: Session, league_id: int, user: User) -> League:
    """La ligue, si le joueur en est membre ; sinon 404 (on ne révèle pas son existence)."""
    league = db.get(League, league_id)
    if league is None or league_store.membership(db, league_id, user.id) is None:
        raise HTTPException(404)
    return league


def share_links(request: Request, league: League, inviter: User) -> dict:
    """Lien d'invitation personnel (?ref= : qui a invité) et lien WhatsApp prêt à envoyer."""
    url = f"{request.url_for('short_join', code=league.code)}?ref={inviter.id}"
    text = translate("league_share_text").format(name=league.name, url=url)
    return {"join_url": url, "share_text": text, "whatsapp_url": "https://wa.me/?text=" + quote(text)}


def timezone(request: Request):
    return resolve_timezone(request.cookies.get("tz"))


# --- Écran 1 : mes ligues ---

@router.get("/leagues")
def leagues_page(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user)):
    done = DONE_MESSAGES.get(request.query_params.get("done", ""))
    return render_leagues(request, db, user, notice=done)


def league_card(db: Session, league: League, member_count: int, user: User, now) -> dict:
    """Résumé d'une ligue pour la liste : ma place, son évolution, visages, dernière activité."""
    ranking, moves = league_store.standing_with_moves(db, league.id)
    activity = league_store.recent_activity(db, league, now)
    return {"league": league, "member_count": member_count,
            "competitions": league_store.competitions_of(db, league.id),
            "me": find_player(ranking, user.id), "move": moves.get(user.id),
            "faces": league_store.member_cards(db, league.id)[:CARD_FACES],
            "activity": activity[0] if activity else None,
            "activity_all": [replace(event, league=league.name) for event in activity]}


def render_leagues(request: Request, db: Session, user: User, error: str | None = None,
                   notice: str | None = None, form: dict | None = None, status_code: int = 200):
    now = utc_now()
    cards = [league_card(db, league, count, user, now)
             for league, count in league_store.my_leagues(db, user.id)]
    context = {"user": user, "cards": cards, "error": error, "notice": notice,
               "form": form or {}, "now": now, "tz": timezone(request),
               "to_predict": matches_to_predict(db, user, now)}
    return templates.TemplateResponse(request, "leagues.html", context, status_code=status_code)


@router.post("/leagues/join")
def join_by_code(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user), code: str = Form("")):
    league = league_store.find_by_code(db, code)
    if league is None:
        return render_leagues(request, db, user, error="error_league_code",
                              form={"code": code}, status_code=400)
    result = league_store.join_league(db, league, user, utc_now())
    if result.error:  # code tapé : on explique pourquoi, même si déjà membre
        return render_leagues(request, db, user, error=result.error, form={"code": code},
                              status_code=400)
    return redirect(f"/leagues/{league.id}?joined=1")


# --- Écran 3 : créer une ligue ---

@router.get("/leagues/new")
def new_league_page(request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_user)):
    return render_create(request, db, user)


def form_context(db: Session, form: dict) -> dict:
    """Données du formulaire de ligue (création et réglages)."""
    rules = current_rules(db)
    return {"form": form, "colors": LEAGUE_COLORS,
            "available_competitions": league_store.active_competitions(db),
            "exact_points": rules.winner_points + rules.exact_bonus,
            "winner_points": rules.winner_points}


def render_create(request: Request, db: Session, user: User, error: str | None = None,
                  form: dict | None = None, status_code: int = 200):
    context = {"user": user, "error": error,
               **form_context(db, form or {"color": LEAGUE_COLORS[0], "competitions": []})}
    return templates.TemplateResponse(request, "league_new.html", context, status_code=status_code)


def chosen_competitions(db: Session, values: list[str]) -> list[int]:
    return clean_competition_ids(values, {c.id for c in league_store.active_competitions(db)})


@router.post("/leagues")
def create_league(request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_user), name: str = Form(""),
                  color: str = Form(""), competitions: list[str] = Form([])):
    competition_ids = chosen_competitions(db, competitions)
    result = league_store.create_league(db, user, name, utc_now(), color, competition_ids)
    if result.error:
        form = {"name": name, "color": color, "competitions": competition_ids}
        return render_create(request, db, user, error=result.error, form=form, status_code=400)
    return redirect(f"/leagues/{result.league.id}/ready")


@router.get("/leagues/{league_id}/ready")
def ready_page(league_id: int, request: Request, db: Session = Depends(get_db),
               user: User = Depends(require_user)):
    """Écran de succès après la création : tout pousse à inviter."""
    league = member_league(db, league_id, user)
    context = {"user": user, "league": league, **share_links(request, league, user)}
    return templates.TemplateResponse(request, "league_ready.html", context)


# --- Écran 2 : détail d'une ligue ---

@router.get("/leagues/{league_id}")
def league_page(league_id: int, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_user)):
    league = member_league(db, league_id, user)
    params = request.query_params
    tab = params.get("tab") if params.get("tab") in TABS else TABS[0]
    now = utc_now()
    members = league_store.member_cards(db, league.id)
    ranking, moves = league_store.standing_with_moves(db, league.id)
    me = find_player(ranking, user.id)
    context = {
        "user": user, "league": league, "tab": tab, "now": now, "tz": timezone(request),
        "notice": "league_joined" if params.get("joined") else None,
        "members": members, "photo_ids": {m.user_id for m in members if m.has_photo},
        "competitions": league_store.competitions_of(db, league.id),
        "is_owner": league.owner_id == user.id, "me": me, "gap": gap_to_leader(ranking, me),
        "moves": moves, **share_links(request, league, user),
        **next_match_context(db, league, members, user, now),
    }
    if tab == "ranking":
        context.update(ranking_context(db, league, ranking, members, user, params.get("all")))
    else:
        context.update(matches_context(db, league, user, params.get("match")))
    response = templates.TemplateResponse(request, "league.html", context)
    # La dernière ligue ouverte devient la ligue principale (accueil, Profil, Résultats)
    response.set_cookie(LEAGUE_COOKIE, str(league.id), max_age=LEAGUE_COOKIE_AGE,
                        httponly=True, samesite="lax")
    return response


def next_match_context(db: Session, league: League, members, user: User, now) -> dict:
    """Prochain match : qui a déjà joué et tendance V/N/D, jamais les scores des autres."""
    match = league_store.next_open_match(db, league.id, now)
    if match is None:
        return {"next_match": None}
    players = league_store.match_players(db, league.id, match.id)
    played_ids = {user_id for user_id, _, _ in players}
    return {"next_match": match, "deadline": prediction_deadline(match.kickoff_at).isoformat(),
            "trend": league_trend([(h, a) for _, h, a in players]),
            "played": [m for m in members if m.user_id in played_ids],
            "i_played": user.id in played_ids}


def ranking_context(db: Session, league: League, ranking, members, user: User, show_all) -> dict:
    rows = standings(ranking, [(m.user_id, m.nickname) for m in members])
    podium = ranking[:3]
    rest = rows[len(podium):]
    best, worst = week_extremes(league_store.last_week_ranking(db, league.id))
    if not podium:  # personne n'a encore de points : le message du podium suffit
        rest = []
    return {"podium": podium, "rows": rest if show_all else ranking_preview(rest, user.id, PREVIEW_ROWS),
            "show_all": bool(show_all), "hidden_rows": len(rest) > PREVIEW_ROWS,
            "week_best": best, "week_worst": worst}


def matches_context(db: Session, league: League, user: User, wanted: str | None) -> dict:
    """Onglet Matchs : un match terminé (le dernier par défaut) et les pronos de la ligue.

    Seuls les matchs terminés sont proposés : un pronostic n'est jamais montré avant le coup d'envoi.
    """
    matches = league_store.finished_matches(db, league.id)
    match = next((m for m in matches if str(m.id) == wanted), matches[0] if matches else None)
    if match is None:
        return {"finished": [], "match": None}
    picks = sort_league_predictions(league_store.match_predictions(db, league.id, match.id), user.id)
    return {"finished": matches, "match": match, "picks": picks,
            "exact_count": sum(1 for _, _, pick in picks if pick and pick.is_exact)}


# --- Réglages, départ, retrait d'un membre, suppression ---

@router.get("/leagues/{league_id}/settings")
def settings_page(league_id: int, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_user)):
    return render_settings(request, db, member_league(db, league_id, user), user,
                           notice="league_saved" if request.query_params.get("saved") else None)


def render_settings(request: Request, db: Session, league: League, user: User,
                    error: str | None = None, notice: str | None = None, form: dict | None = None,
                    status_code: int = 200):
    form = form or {"name": league.name, "color": league.color,
                    "competitions": [c.id for c in league_store.competitions_of(db, league.id)]}
    context = {"user": user, "league": league, "members": league_store.member_cards(db, league.id),
               "is_owner": league.owner_id == user.id, "max_members": league_max_members(db),
               "error": error, "notice": notice, **form_context(db, form)}
    return templates.TemplateResponse(request, "league_settings.html", context,
                                      status_code=status_code)


@router.post("/leagues/{league_id}/settings")
def save_settings(league_id: int, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_user), name: str = Form(""),
                  color: str = Form(""), competitions: list[str] = Form([])):
    league = member_league(db, league_id, user)
    competition_ids = chosen_competitions(db, competitions)
    error = league_store.update_league(db, league, user, name, color, competition_ids)
    if error:
        db.rollback()
        form = {"name": name, "color": color, "competitions": competition_ids}
        return render_settings(request, db, league, user, error=error, form=form,
                               status_code=403 if error == "error_not_league_owner" else 400)
    return redirect(f"/leagues/{league.id}/settings?saved=1")


@router.post("/leagues/{league_id}/leave")
def leave(league_id: int, request: Request, db: Session = Depends(get_db),
          user: User = Depends(require_user)):
    league = member_league(db, league_id, user)
    error = league_store.leave_league(db, league, user)
    if error:
        return render_settings(request, db, league, user, error=error, status_code=403)
    return redirect("/leagues?done=left")


@router.post("/leagues/{league_id}/members/{member_id}/remove")
def remove(league_id: int, member_id: int, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_user)):
    league = member_league(db, league_id, user)
    error = league_store.remove_member(db, league, user, member_id)
    if error:
        return render_settings(request, db, league, user, error=error, status_code=403)
    return redirect(f"/leagues/{league.id}/settings")


@router.post("/leagues/{league_id}/delete")
def delete(league_id: int, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_user), confirm: str = Form("")):
    league = member_league(db, league_id, user)
    if confirm != "yes":
        return render_settings(request, db, league, user, error="error_confirm_delete",
                               status_code=400)
    error = league_store.delete_league(db, league, user)
    if error:
        return render_settings(request, db, league, user, error=error, status_code=403)
    return redirect("/leagues?done=deleted")


# --- Lien d'invitation ---

@router.get("/j/{code}", name="short_join")
def short_join(code: str, request: Request):
    """Lien court partagé (/j/CODE) : même page que /join/CODE."""
    query = request.url.query
    return redirect(f"/join/{quote(code)}" + (f"?{query}" if query else ""))


@router.get("/join/{code}", name="join_page")
def join_page(code: str, request: Request, db: Session = Depends(get_db),
              user: User | None = Depends(current_user)):
    league = league_store.find_by_code(db, code)
    if league is None:
        return render_join(request, db, None, user, error="error_league_code", status_code=404)
    if user and league_store.membership(db, league.id, user.id):
        return redirect(f"/leagues/{league.id}")
    return render_join(request, db, league, user, ref=request.query_params.get("ref", ""))


def render_join(request: Request, db: Session, league: League | None, user: User | None,
                error: str | None = None, status_code: int = 200, ref: str = ""):
    ref = ref if ref.isdigit() else ""  # parrain gardé à travers l'inscription ou la connexion
    next_url = f"/join/{league.code}" + (f"?ref={ref}" if ref else "") if league else "/"
    context = {"user": user, "league": league, "error": error, "ref": ref,
               "member_count": league_store.member_count(db, league.id) if league else 0,
               "next": next_url}
    return templates.TemplateResponse(request, "join.html", context, status_code=status_code)


def join_and_redirect(request: Request, db: Session, league: League, user: User, on_error,
                      ref: str | None = None):
    result = league_store.join_league(db, league, user, utc_now(), ref)
    if result.error == "error_already_member":
        return redirect(f"/leagues/{league.id}")  # déjà membre : on l'emmène simplement à sa ligue
    if result.error:
        return on_error(result.error)
    return redirect(f"/leagues/{league.id}?joined=1")


@router.post("/join/{code}")
def join_by_link(code: str, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user), ref: str = Form("")):
    league = league_store.find_by_code(db, code)
    if league is None:
        return render_join(request, db, None, user, error="error_league_code", status_code=404)
    return join_and_redirect(request, db, league, user, on_error=lambda error: render_join(
        request, db, league, user, error=error, status_code=400, ref=ref), ref=ref)
