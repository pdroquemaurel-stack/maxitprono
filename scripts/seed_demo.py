"""Données de démonstration pour tester le jeu sans l'API foot.

Crée une compétition « Démo », des matchs à venir à pronostiquer, des joueurs
fictifs (pseudos « demo_… », PIN 0000) et des matchs passés déjà notés pour
remplir les classements. Les matchs démo n'ont pas d'identifiant API :
les imports ne les touchent jamais.

Usage :
  python -m scripts.seed_demo            # crée les données (relançable sans doublon)
  python -m scripts.seed_demo --finish   # termine les matchs démo ouverts, calcule les points
  python -m scripts.seed_demo --reset    # supprime toutes les données démo

À réserver aux tests : ne pas lancer sur la base de production.
"""
import argparse
import random
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.jobs.score_predictions import score_finished_matches
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.providers import DEMO
from app.services.accounts import hash_pin
from app.services.deadlines import is_prediction_open
from app.services.scoring import ScoringRules

DEMO_COMPETITION_ID = "demo"  # identifiant chez le « fournisseur » démo
DEMO_COMPETITION_NAME = "Démo"
DEMO_PREFIX = "demo_"
DEMO_PIN = "0000"
DEMO_PLAYERS = [("demo_Samuel", "CM"), ("demo_Aminata", "BF"), ("demo_Eto", "CM"),
                ("demo_Fatou", "BF"), ("demo_Junior", "CM"), ("demo_Ines", "FR")]
TEAMS = ["Lions", "Étalons", "Éléphants", "Aigles", "Pharaons", "Léopards",
         "Lions de l'Atlas", "Black Stars", "Super Eagles", "Fennecs"]
UPCOMING_COUNT = 8  # matchs à pronostiquer sur les 5 prochains jours
PAST_COUNT = 10  # matchs terminés sur les 2 dernières semaines


# --- Création ---

def _find_demo_competition(db: Session) -> Competition | None:
    return db.scalar(select(Competition).where(Competition.provider == DEMO,
                                               Competition.external_id == DEMO_COMPETITION_ID))


def demo_competition(db: Session) -> Competition:
    competition = _find_demo_competition(db)
    if competition is None:
        competition = Competition(provider=DEMO, external_id=DEMO_COMPETITION_ID,
                                  name=DEMO_COMPETITION_NAME,
                                  country="World", is_active=True)
        db.add(competition)
        db.commit()
    return competition


def demo_players(db: Session, now: datetime) -> list[User]:
    """Crée les joueurs fictifs manquants, inscrits il y a 1 à 30 jours."""
    players = []
    pin_hash = None
    for position, (nickname, country) in enumerate(DEMO_PLAYERS):
        user = db.scalar(select(User).where(User.nickname_key == nickname.lower()))
        if user is None:
            pin_hash = pin_hash or hash_pin(DEMO_PIN)  # un seul hash : il est lent exprès
            created_at = now - timedelta(days=30 - position * 5)
            user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash=pin_hash,
                        country_code=country, rules_accepted_at=created_at,
                        created_at=created_at)
            db.add(user)
        players.append(user)
    db.commit()
    return players


def _new_match(competition: Competition, kickoff_at: datetime, rng: random.Random) -> Match:
    home, away = rng.sample(TEAMS, 2)
    return Match(competition=competition, home_team=home, away_team=away, kickoff_at=kickoff_at)


def _random_score(rng: random.Random) -> tuple[int, int]:
    return rng.choice([0, 0, 1, 1, 1, 2, 2, 3]), rng.choice([0, 0, 1, 1, 2, 2, 3])


def _predict_for_players(db: Session, players: list[User], match: Match,
                         rng: random.Random) -> None:
    """Les joueurs fictifs pronostiquent ce match (s'ils ne l'ont pas déjà fait)."""
    for player in players:
        exists = db.scalar(select(Prediction).where(Prediction.user_id == player.id,
                                                    Prediction.match_id == match.id))
        if exists is None:
            home, away = _random_score(rng)
            db.add(Prediction(user_id=player.id, match_id=match.id, home_score=home,
                              away_score=away))


def _demo_matches(db: Session, competition: Competition) -> list[Match]:
    return list(db.scalars(select(Match).where(Match.competition_id == competition.id)))


def add_past_matches(db: Session, competition: Competition, players: list[User],
                     now: datetime, rng: random.Random) -> int:
    """Matchs terminés avec pronostics des joueurs fictifs (une seule fois)."""
    if any(m.status == MatchStatus.FINISHED for m in _demo_matches(db, competition)):
        return 0
    for index in range(PAST_COUNT):
        match = _new_match(competition, now - timedelta(days=14 - index, hours=3), rng)
        match.status = MatchStatus.FINISHED
        match.home_score, match.away_score = _random_score(rng)
        db.add(match)
        db.flush()
        _predict_for_players(db, players, match, rng)
    db.commit()
    return PAST_COUNT


def add_upcoming_matches(db: Session, competition: Competition, now: datetime,
                         rng: random.Random) -> int:
    """Complète jusqu'à 8 matchs ouverts, répartis sur les 5 prochains jours."""
    open_count = sum(1 for m in _demo_matches(db, competition)
                     if is_prediction_open(m.status, m.kickoff_at, now))
    missing = max(0, UPCOMING_COUNT - open_count)
    first_kickoff = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=2)
    for index in range(missing):
        kickoff = first_kickoff + timedelta(hours=15 * index)  # environ 1 à 2 matchs par jour
        db.add(_new_match(competition, kickoff, rng))
    db.commit()
    return missing


def seed(db: Session, now: datetime, rng: random.Random) -> dict:
    competition = demo_competition(db)
    players = demo_players(db, now)
    past = add_past_matches(db, competition, players, now, rng)
    upcoming = add_upcoming_matches(db, competition, now, rng)
    scored = score_finished_matches(db, ScoringRules(), now)
    return {"players": len(players), "past": past, "upcoming": upcoming, "scored": scored}


# --- Fin des matchs ouverts ---

def finish_open_matches(db: Session, now: datetime, rng: random.Random) -> int:
    """Termine les matchs démo encore ouverts, comme s'ils avaient eu lieu il y a 2 h.

    Ils restent visibles sur la page Matchs et comptent dans la semaine en cours.
    """
    competition = demo_competition(db)
    players = demo_players(db, now)
    to_finish = [m for m in _demo_matches(db, competition)
                 if is_prediction_open(m.status, m.kickoff_at, now)]
    for match in to_finish:
        _predict_for_players(db, players, match, rng)
        match.kickoff_at = now - timedelta(hours=2)
        match.status = MatchStatus.FINISHED
        match.home_score, match.away_score = _random_score(rng)
    db.commit()
    score_finished_matches(db, ScoringRules(), now)
    return len(to_finish)


# --- Suppression ---

def reset(db: Session) -> None:
    """Supprime la compétition démo, ses matchs, les joueurs fictifs et leurs pronostics."""
    competition = _find_demo_competition(db)
    demo_user_ids = select(User.id).where(User.nickname_key.startswith(DEMO_PREFIX))
    db.execute(delete(Prediction).where(Prediction.user_id.in_(demo_user_ids)))
    if competition is not None:
        match_ids = select(Match.id).where(Match.competition_id == competition.id)
        db.execute(delete(Prediction).where(Prediction.match_id.in_(match_ids)))
        db.execute(delete(Match).where(Match.competition_id == competition.id))
        db.delete(competition)
    db.execute(delete(User).where(User.nickname_key.startswith(DEMO_PREFIX)))
    db.commit()


def main() -> None:
    from app.db import SessionLocal  # import ici : les tests utilisent leur propre base

    parser = argparse.ArgumentParser()
    parser.add_argument("--finish", action="store_true", help="terminer les matchs démo ouverts")
    parser.add_argument("--reset", action="store_true", help="supprimer les données démo")
    args = parser.parse_args()

    rng = random.Random()
    with SessionLocal() as db:
        if args.reset:
            reset(db)
            print("Données démo supprimées.")
        elif args.finish:
            print(f"Matchs démo terminés : {finish_open_matches(db, utc_now(), rng)}")
            print("Relance « python -m scripts.seed_demo » pour avoir de nouveaux matchs.")
        else:
            result = seed(db, utc_now(), rng)
            print(f"Joueurs fictifs : {result['players']} (PIN {DEMO_PIN}) · "
                  f"matchs passés ajoutés : {result['past']} · "
                  f"matchs à venir ajoutés : {result['upcoming']}")


if __name__ == "__main__":
    main()
