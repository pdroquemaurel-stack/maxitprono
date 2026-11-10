"""Authentification interchangeable.

Les routes utilisent seulement `current_user`, `require_user`, `start_session`
et `end_session` : elles ne savent pas comment le joueur s'est connecté.
"""
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.auth.session import COOKIE_NAME, SESSION_DURATION, read_session, sign_session
from app.config import settings
from app.db import get_db
from app.models import User
from app.models.types import utc_now


class LoginRequired(Exception):
    """Levée quand une page demande un joueur connecté ; redirige vers /login."""


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = read_session(request.cookies.get(COOKIE_NAME), utc_now())
    return db.get(User, user_id) if user_id is not None else None


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise LoginRequired()
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """Page du back-office : 403 (accès interdit) pour un joueur connecté qui n'est pas admin."""
    if not user.is_admin:
        raise HTTPException(403)
    return user


def start_session(response: Response, user_id: int) -> None:
    response.set_cookie(COOKIE_NAME, sign_session(user_id, utc_now()),
                        max_age=int(SESSION_DURATION.total_seconds()),
                        httponly=True, samesite="lax", secure=settings.secure_cookies)


def end_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)
