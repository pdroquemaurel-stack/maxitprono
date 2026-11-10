"""Contrôle d'accès central : un visiteur non connecté ne voit que les pages publiques.

Toute page qui n'est pas dans la liste blanche ci-dessous est privée : une nouvelle
route est donc protégée d'office, sans rien ajouter dans son code.
"""
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth.session import COOKIE_NAME, read_session
from app.models.types import utc_now

# Pages ouvertes à tous : accueil visiteur, connexion, pages légales, routes techniques
PUBLIC_PATHS = {
    "/", "/login", "/register", "/logout",
    "/rules", "/help", "/privacy", "/legal",
    "/health", "/favicon.ico", "/icon.svg", "/sw.js", "/offline",
}
# /internal/ n'utilise pas la session : il est protégé par son propre jeton (SYNC_TOKEN)
PUBLIC_PREFIXES = ("/static/", "/language/", "/internal/")
# Liens d'invitation : le visiteur est envoyé vers l'inscription plutôt que la connexion
INVITE_PREFIXES = ("/j/", "/join/")


def is_public(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES)


def wants_json(request: Request) -> bool:
    """Appel d'API (fetch du JavaScript) plutôt que navigation dans une page."""
    return "application/json" in request.headers.get("accept", "")


def login_redirect(request: Request) -> RedirectResponse:
    """Vers /login (ou /register pour une invitation), avec la page demandée dans `next`."""
    path = request.url.path
    page = "/register" if path.startswith(INVITE_PREFIXES) else "/login"
    if request.method != "GET":
        return RedirectResponse(page, status_code=303)  # un POST ne peut pas être rejoué
    target = path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(f"{page}?next={quote(target, safe='/')}", status_code=303)


async def require_login_for_private_pages(request: Request, call_next):
    user_id = read_session(request.cookies.get(COOKIE_NAME), utc_now())
    request.state.user_id = user_id  # lu par les templates (barre de navigation)
    path = request.url.path
    if user_id is None and not is_public(path):
        if wants_json(request):
            return JSONResponse({"detail": "login_required"}, status_code=401)
        return login_redirect(request)
    response = await call_next(request)
    # Connecté : pas de copie des pages dans le cache, « retour » après déconnexion
    # ne réaffiche rien de lisible. Les réponses qui fixent leur propre cache le gardent.
    cacheable = path.startswith("/static/") or "cache-control" in response.headers
    if user_id is not None and not cacheable:
        response.headers["Cache-Control"] = "no-store"
    return response
