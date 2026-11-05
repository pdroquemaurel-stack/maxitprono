"""Classement de ligue, fil d'activité, temps relatif, choix de la ligue affichée."""
from datetime import UTC, datetime, timedelta

import pytest

from app.i18n import time_ago
from app.models import Competition, Match, Prediction, User
from app.models.match import MatchStatus
from app.services import league_store
from app.services.activity import ACTIVITY_LIMIT, Event, exact_event, join_event, latest_events
from app.services.leaderboards import leaderboard
from app.services.leagues import pick_league

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


# --- Fonctions pures ---

@pytest.mark.parametrize("delta, fr, en", [
    (timedelta(seconds=20), "à l'instant", "just now"),
    (timedelta(minutes=12), "12 min", "12 min"),
    (timedelta(hours=2, minutes=59), "2 h", "2 h"),
    (timedelta(hours=30), "hier", "yesterday"),
    (timedelta(days=3, hours=1), "3 j", "3 d"),
])
def test_time_ago(delta, fr, en):
    assert time_ago(NOW - delta, NOW, "fr") == fr
    assert time_ago(NOW - delta, NOW, "en") == en


def test_join_event_of_owner_is_a_creation():
    assert join_event("Paul", NOW, is_owner=True).kind == "created"
    assert join_event("Awa", NOW, is_owner=False).kind == "joined"


def test_exact_event_names_the_match():
    assert exact_event("Kevin", "Coton Sport", "Canon", NOW).match == "Coton Sport – Canon"


def test_latest_events_sorted_limited_and_within_seven_days():
    events = [Event("joined", f"J{i}", NOW - timedelta(hours=i)) for i in range(8)]
    events += [Event("joined", "Ancien", NOW - timedelta(days=8)),
               Event("exact", "Futur", NOW + timedelta(hours=1))]
    result = latest_events(events, NOW)
    assert [e.nickname for e in result] == ["J0", "J1", "J2", "J3", "J4"]
    assert len(result) == ACTIVITY_LIMIT


@pytest.mark.parametrize("ids, wanted, expected", [
    ([3, 1], "1", 1), ([3, 1], "7", 3), ([3, 1], None, 3), ([3, 1], "abc", 3), ([], "1", None),
])
def test_pick_league(ids, wanted, expected):
    assert pick_league(ids, wanted) == expected


# --- En base ---

def add_user(db, nickname):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x", country_code="CM",
                rules_accepted_at=NOW - timedelta(days=60), created_at=NOW - timedelta(days=60))
    db.add(user)
    db.commit()
    return user


def finished_match(db, kickoff_at, score=(2, 1), home="Coton Sport", away="Canon"):
    competition = db.query(Competition).first() or Competition(
        provider="demo", external_id="demo", name="Démo", is_active=True)
    match = Match(competition=competition, home_team=home, away_team=away, kickoff_at=kickoff_at,
                  status=MatchStatus.FINISHED, home_score=score[0], away_score=score[1])
    db.add(match)
    db.commit()
    return match


def scored(db, user, match, points, exact=False):
    db.add(Prediction(user_id=user.id, match_id=match.id, home_score=2, away_score=1,
                      points=points, is_exact=exact, is_winner=points > 0))
    db.commit()


def test_league_ranking_counts_members_and_matches_after_joining(db):
    paul, awa, outsider = add_user(db, "Paul"), add_user(db, "Awa"), add_user(db, "Moussa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW - timedelta(days=10)).league
    league_store.join_league(db, league, awa, NOW - timedelta(days=2))
    before = finished_match(db, NOW - timedelta(days=5))  # avant l'arrivée d'Awa
    after = finished_match(db, NOW - timedelta(days=1))
    for user in (paul, awa, outsider):
        scored(db, user, before, 3)
        scored(db, user, after, 5, exact=True)

    ranking = {p.nickname: p.points for p in leaderboard(db, league_id=league.id)}

    assert ranking == {"Paul": 8, "Awa": 5}
    assert {p.nickname: p.points for p in leaderboard(db)} == {"Paul": 8, "Awa": 8, "Moussa": 8}


def test_recent_activity_lists_joins_and_exact_scores(db):
    paul, awa, outsider = add_user(db, "Paul"), add_user(db, "Awa"), add_user(db, "Moussa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW - timedelta(days=3)).league
    league_store.join_league(db, league, awa, NOW - timedelta(hours=5))
    match = finished_match(db, NOW - timedelta(hours=2))
    scored(db, paul, match, 5, exact=True)
    scored(db, awa, finished_match(db, NOW - timedelta(days=1)), 5, exact=True)  # avant son arrivée
    scored(db, outsider, match, 5, exact=True)  # pas membre

    events = league_store.recent_activity(db, league, NOW)

    assert [(e.kind, e.nickname) for e in events] == [
        ("exact", "Paul"), ("joined", "Awa"), ("created", "Paul")]
    assert events[0].match == "Coton Sport – Canon"
