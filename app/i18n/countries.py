"""Liste des pays proposés au joueur (codes ISO, noms en français et en anglais)."""
import json
from pathlib import Path

PILOT_COUNTRIES = ("CM", "BF")  # affichés en tête de liste

_COUNTRIES = json.loads((Path(__file__).parent / "countries.json").read_text(encoding="utf-8"))
COUNTRY_CODES = {country["code"] for country in _COUNTRIES}


def country_options(lang: str) -> list[tuple[str, str]]:
    """Liste (code, nom) : pays pilotes d'abord, puis les autres par ordre alphabétique."""
    name_key = lang if lang in ("fr", "en") else "fr"
    pilots = [c for code in PILOT_COUNTRIES for c in _COUNTRIES if c["code"] == code]
    others = sorted((c for c in _COUNTRIES if c["code"] not in PILOT_COUNTRIES),
                    key=lambda c: c[name_key])
    return [(c["code"], c[name_key]) for c in pilots + others]


def country_name(code: str, lang: str) -> str:
    for option_code, name in country_options(lang):
        if option_code == code:
            return name
    return code
