from datetime import UTC, datetime, timedelta

from app.auth.pin_auth import login, register
from app.models import User

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def register_paul(db, **overrides):
    fields = dict(nickname="Paul", pin="1234", country_code="CM", rules_accepted=True, now=NOW)
    fields.update(overrides)
    return register(db, **fields)


def test_register_creates_user(db):
    result = register_paul(db)
    assert result.error is None
    user = db.get(User, result.user_id)
    assert user.nickname == "Paul"
    assert user.country_code == "CM"
    assert user.rules_accepted_at == NOW
    assert user.created_at == NOW
    assert user.pin_hash != "1234"


def test_register_refuses_invalid_fields(db):
    assert register_paul(db, nickname="P").error == "error_nickname_format"
    assert register_paul(db, pin="12").error == "error_pin_format"
    assert register_paul(db, country_code="XX").error == "error_country"
    assert register_paul(db, rules_accepted=False).error == "error_rules_not_accepted"
    assert db.query(User).count() == 0


def test_register_refuses_taken_nickname_whatever_the_case(db):
    register_paul(db)
    assert register_paul(db, nickname="PAUL").error == "error_nickname_taken"


def test_login_with_right_pin(db):
    user_id = register_paul(db).user_id
    assert login(db, "paul", "1234", NOW).user_id == user_id


def test_login_with_wrong_pin_or_unknown_nickname_gives_same_error(db):
    register_paul(db)
    assert login(db, "Paul", "0000", NOW).error == "error_login"
    assert login(db, "Nobody", "1234", NOW).error == "error_login"


def test_five_wrong_pins_lock_the_account(db):
    register_paul(db)
    for _ in range(4):
        assert login(db, "Paul", "0000", NOW).error == "error_login"
    assert login(db, "Paul", "0000", NOW).error == "error_locked"
    # Même le bon PIN est refusé pendant le blocage
    assert login(db, "Paul", "1234", NOW + timedelta(minutes=14)).error == "error_locked"
    # Après 15 minutes, le bon PIN fonctionne
    assert login(db, "Paul", "1234", NOW + timedelta(minutes=15)).user_id is not None


def test_successful_login_resets_failed_attempts(db):
    user_id = register_paul(db).user_id
    login(db, "Paul", "0000", NOW)
    login(db, "Paul", "1234", NOW)
    assert db.get(User, user_id).failed_pin_attempts == 0
