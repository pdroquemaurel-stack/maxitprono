"""Page d'accueil, règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.matches import home_matches, match_context
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
    context.update(matches=matches, to_predict=to_predict)
    return templates.TemplateResponse(request, "home.html", context)


@router.get("/rules")
def rules(request: Request, user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html", {"user": user})


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
