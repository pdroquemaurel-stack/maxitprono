"""Ligues privées : mes ligues, création, invitation par code ou par lien, départ.

Rejoindre une ligue passe toujours par un POST : WhatsApp et les réseaux sociaux
ouvrent les liens partagés pour en faire un aperçu, un GET ne doit rien changer.
"""
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import current_user, require_user
from app.db import get_db
from app.i18n import translate
from app.models import League, User
from app.models.types import utc_now
from app.routes.accounts import redirect
from app.services import league_store
from app.services.settings_store import league_max_members
from app.templating import templates

router = APIRouter()

DONE_MESSAGES = {"left": "league_left", "deleted": "league_deleted"}


def member_league(db: Session, league_id: int, user: User) -> League:
    """La ligue, si le joueur en est membre ; sinon 404 (on ne révèle pas son existence)."""
    league = db.get(League, league_id)
    if league is None or league_store.membership(db, league_id, user.id) is None:
        raise HTTPException(404)
    return league


def share_links(request: Request, league: League, inviter: User) -> dict:
    """Lien d'invitation personnel (?ref= : qui a invité) et lien WhatsApp prêt à envoyer."""
    url = f"{request.url_for('join_page', code=league.code)}?ref={inviter.id}"
    text = translate("league_share_text").format(name=league.name, url=url)
    return {"join_url": url, "share_text": text, "whatsapp_url": "https://wa.me/?text=" + quote(text)}


# --- Mes ligues ---

@router.get("/leagues")
def leagues_page(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user)):
    done = DONE_MESSAGES.get(request.query_params.get("done", ""))
    return render_leagues(request, db, user, notice=done)


def render_leagues(request: Request, db: Session, user: User, error: str | None = None,
                   notice: str | None = None, form: dict | None = None, status_code: int = 200):
    context = {"user": user, "leagues": league_store.my_leagues(db, user.id), "error": error,
               "notice": notice, "form": form or {}}
    return templates.TemplateResponse(request, "leagues.html", context, status_code=status_code)


@router.post("/leagues")
def create_league(request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_user), name: str = Form("")):
    result = league_store.create_league(db, user, name, utc_now())
    if result.error:
        return render_leagues(request, db, user, error=result.error, form={"name": name},
                              status_code=400)
    return redirect(f"/leagues/{result.league.id}?created=1")


@router.post("/leagues/join")
def join_by_code(request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user), code: str = Form("")):
    league = league_store.find_by_code(db, code)
    if league is None:
        return render_leagues(request, db, user, error="error_league_code",
                              form={"code": code}, status_code=400)
    return join_and_redirect(request, db, league, user, on_error=lambda error: render_leagues(
        request, db, user, error=error, form={"code": code}, status_code=400))


def join_and_redirect(request: Request, db: Session, league: League, user: User, on_error,
                      ref: str | None = None):
    result = league_store.join_league(db, league, user, utc_now(), ref)
    if result.error == "error_already_member":
        return redirect(f"/leagues/{league.id}")  # déjà membre : on l'emmène simplement à sa ligue
    if result.error:
        return on_error(result.error)
    return redirect(f"/leagues/{league.id}?joined=1")


# --- Une ligue ---

@router.get("/leagues/{league_id}")
def league_page(league_id: int, request: Request, db: Session = Depends(get_db),
                user: User = Depends(require_user)):
    return render_league(request, db, member_league(db, league_id, user), user)


def render_league(request: Request, db: Session, league: League, user: User,
                  error: str | None = None, status_code: int = 200):
    params = request.query_params
    notice = "league_created" if params.get("created") else (
        "league_joined" if params.get("joined") else None)
    context = {"user": user, "league": league, "members": league_store.members(db, league.id),
               "is_owner": league.owner_id == user.id, "max_members": league_max_members(db),
               "error": error, "notice": notice, **share_links(request, league, user)}
    return templates.TemplateResponse(request, "league.html", context, status_code=status_code)


@router.post("/leagues/{league_id}/leave")
def leave(league_id: int, request: Request, db: Session = Depends(get_db),
          user: User = Depends(require_user)):
    league = member_league(db, league_id, user)
    error = league_store.leave_league(db, league, user)
    if error:
        return render_league(request, db, league, user, error=error, status_code=403)
    return redirect("/leagues?done=left")


@router.post("/leagues/{league_id}/members/{member_id}/remove")
def remove(league_id: int, member_id: int, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_user)):
    league = member_league(db, league_id, user)
    error = league_store.remove_member(db, league, user, member_id)
    if error:
        return render_league(request, db, league, user, error=error, status_code=403)
    return redirect(f"/leagues/{league.id}")


@router.post("/leagues/{league_id}/delete")
def delete(league_id: int, request: Request, db: Session = Depends(get_db),
           user: User = Depends(require_user), confirm: str = Form("")):
    league = member_league(db, league_id, user)
    if confirm != "yes":
        return render_league(request, db, league, user, error="error_confirm_delete",
                             status_code=400)
    error = league_store.delete_league(db, league, user)
    if error:
        return render_league(request, db, league, user, error=error, status_code=403)
    return redirect("/leagues?done=deleted")


# --- Lien d'invitation ---

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


@router.post("/join/{code}")
def join_by_link(code: str, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(require_user), ref: str = Form("")):
    league = league_store.find_by_code(db, code)
    if league is None:
        return render_join(request, db, None, user, error="error_league_code", status_code=404)
    return join_and_redirect(request, db, league, user, on_error=lambda error: render_join(
        request, db, league, user, error=error, status_code=400, ref=ref), ref=ref)
