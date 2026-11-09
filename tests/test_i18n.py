from app.i18n import translate


def test_translate_french_and_english():
    assert translate("home_title", "fr") == "Accueil"
    assert translate("home_title", "en") == "Home"


def test_translate_falls_back_to_key():
    assert translate("unknown_key", "en") == "unknown_key"


def test_format_day():
    from datetime import date

    from app.i18n import format_day
    today = date(2026, 11, 4)  # un mercredi
    assert format_day(today, today, "fr") == "Aujourd'hui"
    assert format_day(date(2026, 11, 5), today, "en") == "Tomorrow"
    assert format_day(date(2026, 11, 10), today, "fr") == "mardi 10 novembre"
    assert format_day(date(2026, 11, 10), today, "en") == "Tuesday 10 November"


def test_french_and_english_have_the_same_keys():
    from app.i18n import TRANSLATIONS
    assert TRANSLATIONS["fr"].keys() == TRANSLATIONS["en"].keys()


def test_closing_when_texts():
    from datetime import UTC, datetime, timedelta

    from app.i18n import closing_when
    kickoff = datetime(2026, 11, 14, 19, 0, tzinfo=UTC)  # un samedi
    deadline = kickoff - timedelta(minutes=10)
    assert closing_when(kickoff, deadline - timedelta(minutes=102), UTC) == "dans 1 h 42"
    assert closing_when(kickoff, deadline - timedelta(minutes=8), UTC, "en") == "in 8 min"
    assert closing_when(kickoff, datetime(2026, 11, 13, 9, 0, tzinfo=UTC), UTC) == "demain"
    assert closing_when(kickoff, datetime(2026, 11, 11, 9, 0, tzinfo=UTC), UTC, "en") == "Saturday"


def test_format_rank_in_french_and_english():
    from app.i18n import format_rank
    assert [format_rank(n, "fr") for n in (1, 2, 3, 11)] == ["1er", "2e", "3e", "11e"]
    assert [format_rank(n, "en") for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101)] == [
        "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "101st"]
