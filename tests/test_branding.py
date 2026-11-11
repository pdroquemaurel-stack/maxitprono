"""Personnalisation : teintes calculées, contraste WCAG, contrôle de saisie (fonctions pures)."""
import pytest

from app.services.branding import (BLACK, WHITE, Branding, changed_fields, clean_color,
                                   contrast_ratio, mix, palette, parse_branding, split_tagline,
                                   text_color_on)


def valid_form(**changes) -> dict:
    form = {"app_name": "Mon Vestiaire", "logo_part1": "Mon", "logo_part2": "Vestiaire",
            "publisher_name": "Max it", "tagline_fr": "Pronostique. Gagne.",
            "tagline_en": "Predict. Win.", "color_primary": "#1F6FEB", "color_dark": "#101828"}
    return form | changes


# --- Couleurs ---

def test_mix_with_white_and_black():
    assert mix("#FF7900", WHITE, 0) == "#FF7900"
    assert mix("#FF7900", WHITE, 1) == WHITE
    assert mix("#FF7900", BLACK, 1) == BLACK
    assert mix("#000000", WHITE, 0.5) == "#808080"


def test_default_palette_is_dark_theme():
    colors = palette("#FF7900", "#0B0E13")
    assert Branding().color_dark == "#0B0E13"
    assert colors.dark == "#0B0E13"
    assert colors.on_primary == BLACK  # texte noir sur l'orange
    assert colors.primary_tint == "rgba(255,121,0,0.14)"


def test_dark_shades_are_mixes_with_white():
    colors = palette("#FF7900", "#0B0E13")
    assert colors.surface == mix("#0B0E13", WHITE, 0.06)
    assert colors.raised == mix("#0B0E13", WHITE, 0.10)
    assert colors.line == mix("#0B0E13", WHITE, 0.14)
    assert colors.line_strong == mix("#0B0E13", WHITE, 0.22)
    assert colors.primary_deep == mix("#FF7900", "#0B0E13", 0.85)


def test_shades_get_lighter_in_order():
    from app.services.branding import luminance
    colors = palette("#FF7900", "#0B0E13")
    steps = [colors.dark, colors.surface, colors.raised, colors.line, colors.line_strong]
    assert [luminance(color) for color in steps] == sorted(luminance(color) for color in steps)


def test_primary_on_dark_is_lightened_orange():
    colors = palette("#FF7900", "#0B0E13")
    assert colors.primary_on_dark == mix("#FF7900", WHITE, 0.25)  # ≈ #FF9A3D, déjà lisible


def test_transparent():
    from app.services.branding import transparent
    assert transparent("#1F6FEB", 0.14) == "rgba(31,111,235,0.14)"


def test_contrast_ratio_extremes():
    assert contrast_ratio(BLACK, WHITE) == pytest.approx(21)
    assert contrast_ratio("#FF7900", "#FF7900") == pytest.approx(1)


@pytest.mark.parametrize("background, text", [
    ("#FF7900", BLACK),  # orange : noir (8.0:1)
    ("#1F6FEB", WHITE),  # bleu : blanc (4.6:1 contre 4.5:1 pour le noir)
    ("#FFF7B0", BLACK),  # jaune très clair : noir
    ("#111111", WHITE),
])
def test_text_color_on_picks_best_contrast(background, text):
    assert text_color_on(background) == text
    assert contrast_ratio(background, text) >= 4.5


@pytest.mark.parametrize("primary", ["#FF7900", "#1F6FEB", "#FFF7B0", "#00FF00", "#777777", "#3A0CA3"])
@pytest.mark.parametrize("dark", ["#0B0E13", "#101828", "#2B2B2B"])
def test_derived_text_colors_are_always_readable(primary, dark):
    colors = palette(primary, dark)
    for background in (colors.dark, colors.surface, colors.raised):
        assert contrast_ratio(colors.primary_on_dark, background) >= 4.5
    assert contrast_ratio(colors.primary, colors.on_primary) >= 4.5


def test_css_variables_names():
    variables = palette("#FF7900", "#0B0E13").css_variables()
    assert variables["--color-primary"] == "#FF7900"
    assert set(variables) == {"--color-primary", "--color-primary-on-dark", "--color-primary-tint",
                              "--color-primary-deep", "--color-on-primary", "--color-dark",
                              "--color-surface", "--color-raised", "--color-line",
                              "--color-line-strong"}


@pytest.mark.parametrize("text, expected", [
    ("#ff7900", "#FF7900"), (" #1F6FEB ", "#1F6FEB"),
    ("red", None), ("#FFF", None), ("#GG0000", None), ("#FF79000", None),
    ("red; background:url(x)", None), ("#FF7900;}", None),
])
def test_clean_color_accepts_only_rrggbb(text, expected):
    assert clean_color(text) == expected


# --- Saisie ---

def test_parse_valid_form_trims_spaces():
    branding, errors = parse_branding(valid_form(app_name="  Mon   Vestiaire ", color_primary="#1f6feb"))
    assert errors == {}
    assert branding.app_name == "Mon Vestiaire" and branding.color_primary == "#1F6FEB"


@pytest.mark.parametrize("name, value, error", [
    ("app_name", "", "error_branding_length"),
    ("app_name", " A ", "error_branding_length"),
    ("logo_part2", "x" * 31, "error_branding_length"),
    ("tagline_fr", "x" * 61, "error_branding_length_tagline"),
    ("app_name", "<b>Mon</b> jeu", "error_branding_characters"),
    ("publisher_name", "{app_name}", "error_branding_characters"),
    ("color_primary", "red; background:url(x)", "error_branding_color"),
    ("color_dark", "#FFFFFF", "error_branding_contrast_dark"),  # texte blanc illisible dessus
])
def test_parse_rejects_bad_values(name, value, error):
    _, errors = parse_branding(valid_form(**{name: value}))
    assert errors == {name: error}


def test_tagline_up_to_60_characters():
    _, errors = parse_branding(valid_form(tagline_fr=Branding().tagline_fr))  # 39 caractères
    assert errors == {}


def test_changed_fields_for_history():
    after = Branding(app_name="Mon Vestiaire", color_primary="#1F6FEB")
    assert changed_fields(Branding(), after) == [
        ("app_name", "MaxitProno", "Mon Vestiaire"), ("color_primary", "#FF7900", "#1F6FEB")]
    assert changed_fields(after, after) == []


@pytest.mark.parametrize("tagline, parts", [
    ("Pronostique les scores. Défie tes amis.", ("Pronostique les scores.", "Défie tes amis.")),
    ("Joue ! Gagne !", ("Joue !", "Gagne !")),
    ("Un seul morceau", ("Un seul morceau", "")),
])
def test_split_tagline(tagline, parts):
    assert split_tagline(tagline) == parts
