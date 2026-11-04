"""Adresse de retour après connexion (paramètre `next`)."""


def safe_next(value: str | None) -> str:
    """Chemin interne au site, sinon l'accueil : évite les redirections vers un autre site."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return "/"
