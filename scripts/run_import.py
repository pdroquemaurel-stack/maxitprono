"""Lance l'import des matchs à la main, chez le fournisseur choisi (DATA_PROVIDER).

Usage :
  python -m scripts.run_import                     # J-3 à J+14 (ou plus, réglage admin) + 1/N/2
  python -m scripts.run_import --season 2024 --from 2024-08-16 --to 2024-08-31
  python -m scripts.run_import --scores            # mise à jour des matchs en cours

Après chaque import, les points des matchs terminés sont calculés.
"""
import argparse
from datetime import date

from app.db import SessionLocal
from app.jobs.import_matches import import_matches
from app.jobs.score_predictions import score_finished_matches
from app.jobs.sync import run_sync
from app.models.types import utc_now
from app.providers import make_provider
from app.providers.base import ProviderError
from app.services.settings_store import current_rules


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, help="forcer une saison (ex. 2024)")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat)
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat)
    parser.add_argument("--scores", action="store_true", help="mettre à jour les scores en direct")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.date_from and args.date_to:
            import_period(db, args)
        else:
            result = run_sync(db, make_provider, "scores" if args.scores else "fixtures",
                              utc_now())
            if "error" in result:
                print(f"Arrêt : {result['error']}")
            print(f"Matchs importés ou mis à jour : {result['matches']}")
            if "probabilities" in result:
                print(f"Pourcentages 1/N/2 : {result['probabilities']}")
            print(f"Pronostics calculés : {result['predictions_scored']}")


def import_period(db, args) -> None:
    """Import d'une période choisie (--from / --to), par exemple une saison passée."""
    try:
        count = import_matches(db, make_provider(db), args.date_from, args.date_to, args.season)
        print(f"Matchs importés : {count}")
    except ProviderError as exc:
        print(f"Arrêt : {exc}")
    # Calcul des points après chaque import, même partiel
    print(f"Pronostics calculés : {score_finished_matches(db, current_rules(db), utc_now())}")


if __name__ == "__main__":
    main()
