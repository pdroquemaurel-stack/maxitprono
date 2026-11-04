"""Lance l'import des matchs à la main.

Usage :
  python -m scripts.run_import                     # J-3 à J+14, saisons en cours
  python -m scripts.run_import --season 2024 --from 2024-08-16 --to 2024-08-31
  python -m scripts.run_import --scores            # mise à jour des matchs en cours

Après chaque import, les points des matchs terminés sont calculés.
"""
import argparse
from datetime import date

from app.db import SessionLocal
from app.jobs.import_matches import import_matches, import_upcoming_matches, update_live_scores
from app.jobs.score_predictions import score_finished_matches
from app.models.types import utc_now
from app.providers.api_football import ApiFootballError, make_client
from app.services.scoring import ScoringRules


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, help="forcer une saison (ex. 2024)")
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat)
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat)
    parser.add_argument("--scores", action="store_true", help="mettre à jour les scores en direct")
    args = parser.parse_args()

    with SessionLocal() as db:
        client = make_client(db)
        try:
            if args.scores:
                print(f"Matchs mis à jour : {update_live_scores(db, client, utc_now())}")
            elif args.date_from and args.date_to:
                count = import_matches(db, client, args.date_from, args.date_to, args.season)
                print(f"Matchs importés : {count}")
            else:
                print(f"Matchs importés : {import_upcoming_matches(db, client, date.today())}")
        except ApiFootballError as exc:
            print(f"Arrêt : {exc}")
        # Calcul des points après chaque import, même partiel
        print(f"Pronostics calculés : {score_finished_matches(db, ScoringRules(), utc_now())}")


if __name__ == "__main__":
    main()
