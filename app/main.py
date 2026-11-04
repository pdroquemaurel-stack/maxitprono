"""Création de l'application FastAPI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.auth import LoginRequired
from app.routes import accounts, home, matches

app = FastAPI(title="MaxitProno")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(home.router)
app.include_router(accounts.router)
app.include_router(matches.router)


@app.exception_handler(LoginRequired)
def redirect_to_login(request, exc):
    return RedirectResponse("/login", status_code=303)
