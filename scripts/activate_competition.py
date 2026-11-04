"""Active ou désactive une compétition (en attendant le back-office).

Usage : python -m scripts.activate_competition FL1        # active Ligue 1
        python -m scripts.activate_competition FL1 --off  # désactive

L'identifiant est celui du fournisseur choisi par DATA_PROVIDER : un code
football-data.org (FL1, PL, CL…) ou un numéro API-Football (61, 39, 2…).
"""
import argparse

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Competition


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("external_id", help="identifiant de la compétition chez le fournisseur")
    parser.add_argument("--off", action="store_true", help="désactiver")
    args = parser.parse_args()

    with SessionLocal() as db:
        competition = db.scalar(select(Competition).where(
            Competition.provider == settings.data_provider, Competition.external_id == args.external_id))
        if competition is None:
            print("Compétition inconnue : lancer d'abord python -m scripts.check_coverage")
            return
        competition.is_active = not args.off
        db.commit()
        state = "active" if competition.is_active else "inactive"
        print(f"{competition.name} ({competition.country}, saison {competition.season}) : {state}")


if __name__ == "__main__":
    main()
