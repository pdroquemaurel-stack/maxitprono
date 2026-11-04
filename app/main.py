"""Création de l'application FastAPI."""
from pathlib import Path

from urllib.parse import quote

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import LoginRequired
from app.routes import accounts, home, internal, leaderboard, leagues, matches, results

app = FastAPI(title="MaxitProno")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(home.router)
app.include_router(accounts.router)
app.include_router(matches.router)
app.include_router(leaderboard.router)
app.include_router(results.router)
app.include_router(leagues.router)
app.include_router(internal.router)


@app.exception_handler(LoginRequired)
def redirect_to_login(request, exc):
    # Après connexion, le joueur revient sur la page demandée (pages en GET seulement)
    target = request.url.path if request.method == "GET" else ""
    query = f"?next={quote(target)}" if target and target != "/" else ""
    return RedirectResponse(f"/login{query}", status_code=303)
