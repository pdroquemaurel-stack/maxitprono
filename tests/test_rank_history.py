"""Historique des rangs (rank_snapshots), refait à chaque calcul des points."""
from datetime import timedelta

from app.jobs.score_predictions import rescore_all, score_finished_matches
from app.models import Competition, Match, Prediction, RankSnapshot, User
from app.models.match import MatchStatus
from app.models.types import utc_now
from app.services.rank_history import player_ranks, refresh_rank_snapshots
from app.services.scoring import ScoringRules

NOW = utc_now()


def add_user(db, nickname):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x", country_code="CM",
                rules_accepted_at=NOW, created_at=NOW - timedelta(days=60))
    db.add(user)
    db.commit()
    return user


def finished_match(db, days_ago, score=(1, 0)):
    competition = db.query(Competition).first() or Competition(
        provider="demo", external_id="demo", name="Démo", is_active=True)
    match = Match(competition=competition, home_team="A", away_team="B",
                  kickoff_at=NOW - timedelta(days=days_ago), status=MatchStatus.FINISHED,
                  home_score=score[0], away_score=score[1])
    db.add(match)
    db.commit()
    return match


def predict(db, user, match, home, away):
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=home, away_score=away))
    db.commit()


def test_snapshots_follow_scoring(db):
    ali, bea = add_user(db, "Ali"), add_user(db, "Bea")
    day1, day2 = finished_match(db, 5), finished_match(db, 4)
    predict(db, ali, day1, 1, 0)  # 1er jour : Ali 5, Bea 0
    predict(db, bea, day1, 0, 1)
    predict(db, bea, day2, 1, 0)  # 2e jour : 5 partout, Ali reste devant (plus petit id)
    predict(db, ali, day2, 0, 2)
    score_finished_matches(db, ScoringRules(), NOW)

    assert [rank for _, rank in player_ranks(db, ali.id)] == [1, 1]
    assert [rank for _, rank in player_ranks(db, bea.id)] == [2, 2]


def test_climb_is_recorded_day_by_day(db):
    players = [add_user(db, name) for name in ("Ali", "Bea", "Cyr")]
    day1, day2 = finished_match(db, 5, (2, 1)), finished_match(db, 4, (3, 3))
    for player, pick in zip(players, ((2, 1), (1, 0), (0, 1))):
        predict(db, player, day1, *pick)  # Ali 5, Bea 3, Cyr 0
    predict(db, players[2], day2, 3, 3)  # Cyr : score exact, 5 pts, passe devant Bea
    score_finished_matches(db, ScoringRules(), NOW)
    assert [rank for _, rank in player_ranks(db, players[2].id)] == [3, 2]


def test_refresh_only_touches_recent_days(db):
    ali = add_user(db, "Ali")
    old, recent = finished_match(db, 30), finished_match(db, 1)
    predict(db, ali, old, 1, 0)
    predict(db, ali, recent, 1, 0)
    score_finished_matches(db, ScoringRules(), NOW)
    assert db.query(RankSnapshot).count() == 2
    assert refresh_rank_snapshots(db, since=recent.kickoff_at.date()) == 1  # une seule journée refaite
    assert db.query(RankSnapshot).count() == 2


def test_empty_table_is_fully_rebuilt(db):
    ali = add_user(db, "Ali")
    predict(db, ali, finished_match(db, 30), 1, 0)
    score_finished_matches(db, ScoringRules(), NOW)
    db.query(RankSnapshot).delete()
    db.commit()
    assert refresh_rank_snapshots(db, since=NOW.date()) == 1  # la journée d'il y a 30 jours revient


def test_new_scale_rebuilds_everything(db):
    ali, bea = add_user(db, "Ali"), add_user(db, "Bea")
    match = finished_match(db, 10, (2, 0))
    predict(db, ali, match, 2, 0)
    predict(db, bea, match, 1, 0)
    score_finished_matches(db, ScoringRules(), NOW)
    rescore_all(db, ScoringRules(winner_points=1, exact_bonus=9), NOW)
    points = {row.user_id: row.points for row in db.query(RankSnapshot)}
    assert points == {ali.id: 10, bea.id: 1}
