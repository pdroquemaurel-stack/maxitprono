"""Page d'accueil, règles du jeu et vérification de santé."""
from fastapi import APIRouter, Depends, Request

from app.auth import current_user
from app.models import User
from app.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/rules")
def rules(request: Request, user: User | None = Depends(current_user)):
    return templates.TemplateResponse(request, "rules.html", {"user": user})


@router.get("/health")
def health():
    # Utilisé par Render pour vérifier que le service répond
    return {"status": "ok"}
