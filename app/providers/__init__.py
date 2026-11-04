"""Fournisseurs de données foot : seul endroit de l'app qui appelle une API foot."""

# Valeurs de la colonne `provider` (compétitions, matchs, journal des appels)
API_FOOTBALL = "api_football"
FOOTBALL_DATA = "football_data"
DEMO = "demo"  # données de démonstration, jamais touchées par les imports


def make_provider(db):
    """Client du fournisseur choisi par DATA_PROVIDER (voir base.FootballProvider)."""
    # Imports ici : les modules des clients importent les constantes ci-dessus
    from app.config import settings
    from app.providers.api_football import ApiFootballClient
    from app.providers.base import ProviderError
    from app.providers.football_data import FootballDataClient

    if settings.data_provider == FOOTBALL_DATA:
        return FootballDataClient(settings.football_data_api_key, db)
    if settings.data_provider == API_FOOTBALL:
        return ApiFootballClient(settings.api_football_key, db)
    raise ProviderError(f"DATA_PROVIDER inconnu : {settings.data_provider!r} "
                        f"(attendu : {FOOTBALL_DATA} ou {API_FOOTBALL})")
