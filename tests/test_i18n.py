from app.i18n import translate


def test_translate_french_and_english():
    assert translate("home_title", "fr") == "Accueil"
    assert translate("home_title", "en") == "Home"


def test_translate_falls_back_to_key():
    assert translate("unknown_key", "en") == "unknown_key"
