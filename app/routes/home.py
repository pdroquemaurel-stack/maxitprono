"""Page d'accueil, règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.matches import home_matches, match_context
from app.services.leaderboards import leaderboard
from app.services.ranking import find_player
from app.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db),
         user: User | None = Depends(current_user)):
    if user is None:
        return templates.TemplateResponse(request, "home.html", {"user": None})
    now = utc_now()
    matches, to_predict = home_matches(db, user, now)
    context = match_context(request, db, user, matches, now)
    # Classement général complet pour trouver le rang : suffisant pour le POC
    ranking = leaderboard(db)
    context.update(matches=matches, to_predict=to_predict,
                   me=find_player(ranking, user.id), me_total=len(ranking))
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/rules")
def rules(request: Request, user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html", {"user": user})


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
