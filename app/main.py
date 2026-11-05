"""Création de l'application FastAPI."""
import logging
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.auth import LoginRequired
from app.i18n import pick_language, set_language
from app.routes import accounts, admin, home, internal, leaderboard, leagues, matches, results
from app.templating import templates

STATIC_DIR = Path(__file__).parent / "static"
logger = logging.getLogger(__name__)

app = FastAPI(title="MaxitProno")


@app.middleware("http")
async def use_player_language(request, call_next):
    """Langue choisie par le joueur (cookie « lang »), sinon celle du téléphone."""
    set_language(pick_language(request.cookies.get("lang"),
                               request.headers.get("accept-language")))
    return await call_next(request)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(home.router)
app.include_router(accounts.router)
app.include_router(matches.router)
app.include_router(leaderboard.router)
app.include_router(results.router)
app.include_router(leagues.router)
app.include_router(internal.router)
app.include_router(admin.router)


@app.exception_handler(LoginRequired)
def redirect_to_login(request, exc):
    # Après connexion, le joueur revient sur la page demandée (pages en GET seulement)
    target = request.url.path if request.method == "GET" else ""
    query = f"?next={quote(target)}" if target and target != "/" else ""
    return RedirectResponse(f"/login{query}", status_code=303)


# --- Pages d'erreur ---

def error_page(request: Request, kind: str, status_code: int):
    """Page d'erreur aux couleurs du jeu, avec « Réessayer » et « Retour à l'accueil »."""
    set_language(pick_language(request.cookies.get("lang"), request.headers.get("accept-language")))
    return templates.TemplateResponse(request, "error.html", {"user": None, "kind": kind},
                                      status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    # Pages en 404 ; les autres erreurs (et la route /internal, appelée par un robot) restent en JSON
    if exc.status_code == 404 and not request.url.path.startswith("/internal"):
        return error_page(request, "not_found", 404)
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    logger.exception("Erreur sur %s %s", request.method, request.url.path)
    return error_page(request, "server", 500)


# --- Hors connexion (service worker) ---

@app.get("/sw.js", include_in_schema=False)
def service_worker():
    """Servi à la racine : le service worker peut alors intercepter toutes les pages du site."""
    return FileResponse(STATIC_DIR / "js" / "sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})


@app.get("/offline", include_in_schema=False)
def offline(request: Request):
    """Page gardée par le service worker, affichée quand le réseau ne répond pas."""
    response = templates.TemplateResponse(request, "offline.html", {})
    response.headers["Cache-Control"] = "no-cache"
    return response
