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
