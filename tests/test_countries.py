from app.i18n.countries import COUNTRY_CODES, country_name, country_options


def test_pilot_countries_come_first():
    codes = [code for code, _ in country_options("fr")]
    assert codes[:2] == ["CM", "BF"]


def test_country_names_are_translated():
    assert country_name("CI", "fr") == "Côte d'Ivoire"
    assert country_name("CI", "en") == "Ivory Coast"


def test_all_codes_are_two_letters():
    assert all(len(code) == 2 and code.isupper() for code in COUNTRY_CODES)
