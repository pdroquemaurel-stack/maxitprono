"""Création de l'application FastAPI."""
from pathlib import Path

from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import LoginRequired
from app.i18n import pick_language, set_language
from app.routes import accounts, admin, home, internal, leaderboard, leagues, matches, results

app = FastAPI(title="MaxitProno")


@app.middleware("http")
async def use_player_language(request, call_next):
    """Langue choisie par le joueur (cookie « lang »), sinon celle du téléphone."""
    set_language(pick_language(request.cookies.get("lang"),
                               request.headers.get("accept-language")))
    return await call_next(request)


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
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
