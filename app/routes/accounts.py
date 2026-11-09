"""Pages d'inscription, de connexion, de déconnexion ; langue et photos de profil.

La page Profil est dans profile.py."""
from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth import current_user, end_session, start_session
from app.auth import pin_auth
from app.db import get_db
from app.i18n import SUPPORTED_LANGUAGES
from app.models import User
from app.models.types import utc_now
from app.services import league_store
from app.services.accounts import MAX_AVATAR_BYTES, avatar_mime, decode_data_url
from app.services.redirects import safe_next
from app.templating import templates

router = APIRouter()


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)  # 303 : le navigateur refait un GET


def read_avatar(avatar_data: str, avatar_file: UploadFile | None) -> tuple[bytes | None, str, str | None]:
    """Renvoie (octets, type MIME, erreur). (None, "", None) si aucune photo envoyée.

    `avatar_data` : photo déjà réduite par le navigateur (JavaScript).
    `avatar_file` : fichier brut, si le JavaScript n'a pas tourné.
    """
    if avatar_data:
        data = decode_data_url(avatar_data)
        if data is None:
            return None, "", "error_avatar_format"
    elif avatar_file is not None:
        data = avatar_file.file.read(MAX_AVATAR_BYTES + 1)  # on ne lit pas plus que la limite
    else:
        data = None
    if not data:
        return None, "", None
    mime, error = avatar_mime(data)
    return (data, mime, None) if mime else (None, "", error)


# --- Inscription ---

@router.get("/register")
def register_form(request: Request, user: User | None = Depends(current_user)):
    next_url = safe_next(request.query_params.get("next"))
    if user:
        return redirect(next_url)
    return templates.TemplateResponse(request, "register.html", {"form": {}, "next": next_url})


@router.post("/register")
def register_submit(request: Request, db: Session = Depends(get_db),
                    nickname: str = Form(""), pin: str = Form(""), country_code: str = Form(""),
                    rules_accepted: bool = Form(False), avatar_data: str = Form(""),
                    avatar_file: UploadFile | None = File(None), next: str = Form("/")):
    avatar, mime, error = read_avatar(avatar_data, avatar_file)
    result = pin_auth.AuthResult(error=error)
    if error is None:
        result = pin_auth.register(db, nickname, pin, country_code, rules_accepted, utc_now())
    if result.error:
        form = {"nickname": nickname, "country_code": country_code, "rules_accepted": rules_accepted}
        return templates.TemplateResponse(request, "register.html",
                                          {"form": form, "error": result.error,
                                           "next": safe_next(next)}, status_code=400)
    if avatar:
        user = db.get(User, result.user_id)
        user.avatar, user.avatar_mime = avatar, mime
        db.commit()
    response = redirect(after_login(db, result.user_id, safe_next(next)))
    start_session(response, result.user_id)
    return response


def after_login(db: Session, user_id: int, next_url: str) -> str:
    """Où aller après connexion : arrivé par un lien d'invitation, le joueur rejoint
    directement la ligue (c'est un POST, donc un vrai geste du joueur)."""
    return league_store.join_from_invite(db, db.get(User, user_id), next_url, utc_now()) or next_url


# --- Connexion / déconnexion ---

@router.get("/login")
def login_form(request: Request, user: User | None = Depends(current_user)):
    next_url = safe_next(request.query_params.get("next"))
    if user:
        return redirect(next_url)
    return templates.TemplateResponse(request, "login.html", {"form": {}, "next": next_url})


@router.post("/login")
def login_submit(request: Request, db: Session = Depends(get_db),
                 nickname: str = Form(""), pin: str = Form(""), next: str = Form("/")):
    result = pin_auth.login(db, nickname, pin, utc_now())
    if result.error:
        return templates.TemplateResponse(request, "login.html",
                                          {"form": {"nickname": nickname}, "error": result.error,
                                           "next": safe_next(next)}, status_code=400)
    response = redirect(after_login(db, result.user_id, safe_next(next)))
    start_session(response, result.user_id)
    return response


@router.post("/logout")
def logout():
    response = redirect("/")
    end_session(response)
    return response


@router.get("/language/{lang}")
def choose_language(lang: str, request: Request):
    """Choix de la langue : simple lien, mémorisé un an dans le cookie « lang »."""
    response = redirect(safe_next(request.query_params.get("next")))
    if lang in SUPPORTED_LANGUAGES:
        response.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="lax")
    return response


@router.get("/avatars/{user_id}")
def avatar(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or user.avatar is None:
        return Response(status_code=404)
    return Response(user.avatar, media_type=user.avatar_mime,
                    headers={"Cache-Control": "public, max-age=300"})
