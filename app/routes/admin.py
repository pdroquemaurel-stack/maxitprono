"""Back-office (SPEC §9), réservé aux joueurs avec `is_admin` (scripts/make_admin.py)."""
from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import User
from app.models.types import utc_now
from app.routes.accounts import redirect
from app.services.game_settings import parse_settings
from app.services.settings_store import get_settings, save_settings
from app.templating import templates

router = APIRouter(prefix="/admin")


@router.get("")
def admin_home(request: Request, user: User = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/index.html", {"user": user})


@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_admin)):
    rescored = request.query_params.get("rescored")
    context = {"user": user, "settings": get_settings(db), "form": None, "error": None,
               "saved": request.query_params.get("saved"),
               "rescored": int(rescored) if rescored and rescored.isdigit() else None}
    return templates.TemplateResponse(request, "admin/settings.html", context)


@router.post("/settings")
def settings_submit(request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_admin), winner_points: str = Form(""),
                    exact_bonus: str = Form(""), league_max_members: str = Form("")):
    settings, error = parse_settings(winner_points, exact_bonus, league_max_members)
    if error:
        form = {"winner_points": winner_points, "exact_bonus": exact_bonus,
                "league_max_members": league_max_members}
        context = {"user": user, "settings": get_settings(db), "form": form, "error": error,
                   "saved": None, "rescored": None}
        return templates.TemplateResponse(request, "admin/settings.html", context,
                                          status_code=400)
    rescored = save_settings(db, settings, utc_now())
    return redirect(f"/admin/settings?saved=1&rescored={rescored}" if rescored
                    else "/admin/settings?saved=1")
