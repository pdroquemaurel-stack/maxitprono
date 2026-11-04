"""Page d'accueil, règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.matches import matches_to_predict
from app.services.leaderboards import leaderboard
from app.services.ranking import find_player
from app.services.timezones import resolve_timezone
from app.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db),
         user: User | None = Depends(current_user)):
    if user is None:
        return templates.TemplateResponse(request, "home.html", {"user": None})
    now = utc_now()
    # Classement général complet pour le podium et mon rang : suffisant pour le POC
    ranking = leaderboard(db)
    context = {
        "user": user,
        "now": now,
        "tz": resolve_timezone(request.cookies.get("tz")),
        "to_predict": matches_to_predict(db, user, now),
        "podium": ranking[:3],
        "me": find_player(ranking, user.id),
        "total": len(ranking),
    }
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/rules")
def rules(request: Request, user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html", {"user": user})


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
