"""Repart de zéro côté données foot après un changement de fournisseur (DATA_PROVIDER).

Supprime les compétitions qui ne viennent pas du fournisseur actif, avec leurs
matchs (y compris ceux ajoutés à la main) et les pronostics sur ces matchs, puis
enregistre les compétitions du nouveau fournisseur (inactives, à activer avec
scripts.activate_competition).

Sont conservés : les joueurs, le journal des appels, et les données démo
(sauf avec --include-demo).

Usage :
  python -m scripts.reset_football_data                  # simulation : affiche sans rien supprimer
  python -m scripts.reset_football_data --yes            # supprime, puis importe les compétitions
  python -m scripts.reset_football_data --yes --include-demo
"""
import argparse

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Competition, Match, Prediction
from app.providers import DEMO


def competitions_to_delete(db: Session, keep_provider: str,
                           include_demo: bool = False) -> list[Competition]:
    """Compétitions d'un autre fournisseur que `keep_provider`."""
    kept = [keep_provider] if include_demo else [keep_provider, DEMO]
    return list(db.scalars(select(Competition).where(Competition.provider.not_in(kept))
                           .order_by(Competition.provider, Competition.name)))


def count_data(db: Session, competitions: list[Competition]) -> dict:
    """Nombre de compétitions, matchs et pronostics concernés."""
    ids = [c.id for c in competitions]
    match_ids = select(Match.id).where(Match.competition_id.in_(ids))
    return {
        "competitions": len(ids),
        "matches": db.scalar(select(func.count()).select_from(Match)
                             .where(Match.competition_id.in_(ids))),
        "predictions": db.scalar(select(func.count()).select_from(Prediction)
                                 .where(Prediction.match_id.in_(match_ids))),
    }


def delete_competitions(db: Session, competitions: list[Competition]) -> None:
    """Supprime les compétitions, leurs matchs et les pronostics sur ces matchs."""
    ids = [c.id for c in competitions]
    match_ids = select(Match.id).where(Match.competition_id.in_(ids))
    db.execute(delete(Prediction).where(Prediction.match_id.in_(match_ids)))
    db.execute(delete(Match).where(Match.competition_id.in_(ids)))
    db.execute(delete(Competition).where(Competition.id.in_(ids)))
    db.commit()


def main() -> None:
    # Imports ici : les tests utilisent leur propre base et ne lisent pas la configuration
    from app.config import settings
    from app.db import SessionLocal
    from app.jobs.import_competitions import import_competitions
    from app.providers import make_provider
    from app.providers.base import ProviderError

    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="supprimer pour de bon")
    parser.add_argument("--include-demo", action="store_true", help="supprimer aussi la démo")
    args = parser.parse_args()

    with SessionLocal() as db:
        competitions = competitions_to_delete(db, settings.data_provider, args.include_demo)
        counts = count_data(db, competitions)
        print(f"Fournisseur actif : {settings.data_provider}")
        for competition in competitions:
            print(f"  à supprimer : [{competition.provider}] {competition.name} "
                  f"({competition.external_id})")
        print(f"Total : {counts['competitions']} compétition(s), {counts['matches']} match(s), "
              f"{counts['predictions']} pronostic(s). Les joueurs sont conservés.")

        if not args.yes:
            print("Simulation : rien n'a été supprimé. Relancer avec --yes pour appliquer.")
            return
        try:
            provider = make_provider(db)  # avant de supprimer : une clé manquante arrête tout
        except ProviderError as exc:
            print(f"Arrêt, rien n'a été supprimé : {exc}")
            return
        delete_competitions(db, competitions)
        print("Suppression faite.")
        try:
            summaries = import_competitions(db, provider)
        except ProviderError as exc:
            print(f"Import des compétitions impossible : {exc}")
            print("Relancer plus tard : python -m scripts.check_coverage")
            return
        print(f"{len(summaries)} compétition(s) {provider.name} enregistrée(s), inactives. "
              "Activer avec : python -m scripts.activate_competition <code>")


if __name__ == "__main__":
    main()
