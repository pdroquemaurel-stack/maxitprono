"""Vérifie la couverture des compétitions du POC chez le fournisseur choisi (DATA_PROVIDER).

Usage : python -m scripts.check_coverage

Coût : 1 appel (football-data.org) ou environ 10 (API-Football). Les compétitions
trouvées sont enregistrées en base (inactives), pour pouvoir les activer ensuite
sans nouvel appel avec scripts.activate_competition.
"""
from app.db import SessionLocal
from app.jobs.import_competitions import import_competitions
from app.providers import make_provider
from app.providers.base import ProviderError


def format_row(s: dict) -> str:
    season = f"{s['season']}{'' if s['is_current'] else ' (pas en cours)'}"
    return (f"{s['external_id']:>5} | {s['name'][:28]:<28} | {s['country'][:13]:<13} | "
            f"{season:<18} | {s['start']} → {s['end']} | {s['coverage']}")


def main() -> None:
    with SessionLocal() as db:
        try:
            provider = make_provider(db)
            summaries = import_competitions(db, provider)
        except ProviderError as exc:
            print(f"Arrêt : {exc}")
            return
        print(f"Fournisseur : {provider.name} — {len(summaries)} compétition(s)")
        for summary in summaries:
            print(format_row(summary))


if __name__ == "__main__":
    main()
