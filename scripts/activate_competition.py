"""Active ou désactive une compétition (en attendant le back-office).

Usage : python -m scripts.activate_competition 61        # active Ligue 1
        python -m scripts.activate_competition 61 --off  # désactive
"""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Competition


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("api_id", type=int, help="identifiant API-Football")
    parser.add_argument("--off", action="store_true", help="désactiver")
    args = parser.parse_args()

    with SessionLocal() as db:
        competition = db.scalar(select(Competition).where(Competition.api_id == args.api_id))
        if competition is None:
            print("Compétition inconnue : lancer d'abord python -m scripts.check_coverage")
            return
        competition.is_active = not args.off
        db.commit()
        state = "active" if competition.is_active else "inactive"
        print(f"{competition.name} ({competition.country}, saison {competition.season}) : {state}")


if __name__ == "__main__":
    main()
