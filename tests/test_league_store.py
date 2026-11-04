from datetime import UTC, datetime, timedelta

from app.models import League, LeagueMember, User
from app.services import league_store
from app.services.leagues import MAX_LEAGUES_PER_PLAYER

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def add_user(db, nickname):
    user = User(nickname=nickname, nickname_key=nickname.lower(), pin_hash="x",
                country_code="CM", rules_accepted_at=NOW)
    db.add(user)
    db.commit()
    return user


def test_create_league_makes_owner_a_member(db):
    paul = add_user(db, "Paul")
    result = league_store.create_league(db, paul, "  Bureau   Casa ", NOW)
    league = result.league
    assert result.error is None
    assert (league.name, league.owner_id, len(league.code)) == ("Bureau Casa", paul.id, 6)
    assert [m.user_id for m in league_store.members(db, league.id)] == [paul.id]


def test_create_league_refuses_bad_name(db):
    result = league_store.create_league(db, add_user(db, "Paul"), "ab", NOW)
    assert result.error == "error_league_name"
    assert db.query(League).count() == 0


def test_create_refused_at_player_limit(db):
    paul = add_user(db, "Paul")
    for i in range(MAX_LEAGUES_PER_PLAYER):
        league_store.create_league(db, paul, f"Ligue {i}", NOW)
    assert league_store.create_league(db, paul, "Une de trop", NOW).error == "error_too_many_leagues"


def test_join_by_code_typed_loosely(db):
    paul, awa = add_user(db, "Paul"), add_user(db, "Awa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    found = league_store.find_by_code(db, " " + league.code.lower() + " ")
    assert found.id == league.id
    assert league_store.join_league(db, found, awa, NOW + timedelta(hours=1)).error is None
    assert league_store.member_count(db, league.id) == 2


def test_join_twice_is_refused(db):
    paul = add_user(db, "Paul")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    assert league_store.join_league(db, league, paul, NOW).error == "error_already_member"
    assert league_store.member_count(db, league.id) == 1


def test_my_leagues_most_recent_first_with_member_counts(db):
    paul, awa = add_user(db, "Paul"), add_user(db, "Awa")
    first = league_store.create_league(db, paul, "Première", NOW).league
    second = league_store.create_league(db, awa, "Seconde", NOW).league
    league_store.join_league(db, second, paul, NOW + timedelta(days=1))
    assert [(l.name, count) for l, count in league_store.my_leagues(db, paul.id)] == [
        ("Seconde", 2), ("Première", 1)]
    assert first.id != second.id


def test_member_leaves_but_owner_cannot(db):
    paul, awa = add_user(db, "Paul"), add_user(db, "Awa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    league_store.join_league(db, league, awa, NOW)
    assert league_store.leave_league(db, league, paul) == "error_owner_cannot_leave"
    assert league_store.leave_league(db, league, awa) is None
    assert league_store.member_count(db, league.id) == 1


def test_owner_removes_a_member(db):
    paul, awa = add_user(db, "Paul"), add_user(db, "Awa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    league_store.join_league(db, league, awa, NOW)
    assert league_store.remove_member(db, league, awa, paul.id) == "error_not_league_owner"
    assert league_store.remove_member(db, league, paul, awa.id) is None
    assert league_store.membership(db, league.id, awa.id) is None


def test_only_owner_deletes_the_league(db):
    paul, awa = add_user(db, "Paul"), add_user(db, "Awa")
    league = league_store.create_league(db, paul, "Bureau Casa", NOW).league
    league_store.join_league(db, league, awa, NOW)
    assert league_store.delete_league(db, league, awa) == "error_not_league_owner"
    assert league_store.delete_league(db, league, paul) is None
    assert db.query(League).count() == 0 and db.query(LeagueMember).count() == 0
    assert db.query(User).count() == 2
