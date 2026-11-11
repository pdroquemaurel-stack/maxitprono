"""Personnalisation (nom du jeu, logo, couleurs) : valeurs par défaut, contrôle de saisie, palette.

Fonctions pures : aucune base. La lecture en base et le cache sont dans branding_store.py.
"""
import re
from dataclasses import asdict, dataclass, fields

NAME_LENGTH = (2, 30)
TAGLINE_LENGTH = (2, 60)  # le slogan par défaut fait 39 caractères
HEX_COLOR = re.compile(r"#[0-9A-F]{6}")
# Refusés dans les textes : balises HTML, et accolades qui casseraient les traductions « {app_name} »
FORBIDDEN_CHARACTERS = set("<>{}")
MIN_CONTRAST = 4.5  # WCAG AA, texte normal

WHITE = "#FFFFFF"
BLACK = "#000000"


@dataclass(frozen=True)
class Branding:
    app_name: str = "MaxitProno"
    logo_part1: str = "Maxit"
    logo_part2: str = "Prono"
    publisher_name: str = "Max it"
    tagline_fr: str = "Pronostique les scores. Défie tes amis."
    tagline_en: str = "Predict the scores. Challenge your friends."
    color_primary: str = "#FF7900"
    color_dark: str = "#0B0E13"

    def tagline(self, lang: str) -> str:
        return self.tagline_en if lang == "en" else self.tagline_fr

    @property
    def palette(self) -> "Palette":
        return palette(self.color_primary, self.color_dark)


FIELDS = [field.name for field in fields(Branding)]


# --- Couleurs ---

def hex_to_rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def mix(color: str, other: str, ratio: float) -> str:
    """Mélange `color` avec `other` : ratio 0 = color, ratio 1 = other.

    Ex. mix("#FF7900", WHITE, 0.91) = "#FFF3E8" (orange très pâle).
    """
    pairs = zip(hex_to_rgb(color), hex_to_rgb(other))
    return rgb_to_hex(tuple(round(a + (b - a) * ratio) for a, b in pairs))


def luminance(color: str) -> float:
    """Luminance relative WCAG : 0 pour le noir, 1 pour le blanc."""
    def channel(value: int) -> float:
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(value) for value in hex_to_rgb(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(color: str, other: str) -> float:
    """Ratio de contraste WCAG, de 1 (identiques) à 21 (noir sur blanc)."""
    darker, lighter = sorted((luminance(color), luminance(other)))
    return (lighter + 0.05) / (darker + 0.05)


def text_color_on(background: str) -> str:
    """Noir ou blanc : celui qui contraste le plus avec le fond."""
    return BLACK if contrast_ratio(BLACK, background) >= contrast_ratio(WHITE, background) else WHITE


def lighten_until_readable(color: str, background: str, start: float) -> str:
    """Éclaircit `color` (mélange avec du blanc, à partir de `start`) jusqu'à être lisible sur `background`."""
    ratio = start
    while ratio < 1 and contrast_ratio(mix(color, WHITE, ratio), background) < MIN_CONTRAST:
        ratio += 0.02
    return mix(color, WHITE, min(ratio, 1))


def transparent(color: str, opacity: float) -> str:
    """« #FF7900 », 0.14 -> « rgba(255,121,0,0.14) » : teinte légère posée sur le fond sombre."""
    red, green, blue = hex_to_rgb(color)
    return f"rgba({red},{green},{blue},{opacity})"


@dataclass(frozen=True)
class Palette:
    """Variables CSS de la marque, injectées dans <style>:root{…}</style> (voir _brand_style.html).

    Thème sombre : `dark` est le fond de l'application, les autres fonds en sont des
    éclaircissements (mélange avec du blanc).
    """
    primary: str  # boutons principaux, onglet actif, cases à remplir
    primary_on_dark: str  # liens et textes de la couleur principale sur le fond sombre (≈ #FF9A3D)
    primary_tint: str  # couleur principale à 14 % (pastilles « à faire »), en rgba
    primary_deep: str  # fond d'une case de score vide à remplir
    on_primary: str  # texte posé sur la couleur principale : noir ou blanc
    dark: str  # fond de l'application
    surface: str  # cartes (≈ #151A21)
    raised: str  # carte mise en avant, case de score remplie (≈ #1A1F27)
    line: str  # bordures, séparateurs (≈ #232A33)
    line_strong: str  # bordures de champs, pointillés (≈ #3A4350)

    def css_variables(self) -> dict[str, str]:
        return {"--color-" + name.replace("_", "-"): value for name, value in asdict(self).items()}


def palette(primary: str, dark: str) -> Palette:
    """Toutes les teintes calculées à partir des deux couleurs choisies dans l'admin."""
    raised = mix(dark, WHITE, 0.10)
    return Palette(primary=primary,
                   # lisible sur le fond le plus clair où il apparaît (donc aussi sur le fond et les cartes)
                   primary_on_dark=lighten_until_readable(primary, raised, 0.25),
                   primary_tint=transparent(primary, 0.14),
                   primary_deep=mix(primary, dark, 0.85),
                   on_primary=text_color_on(primary),
                   dark=dark,
                   surface=mix(dark, WHITE, 0.06),
                   raised=raised,
                   line=mix(dark, WHITE, 0.14),
                   line_strong=mix(dark, WHITE, 0.22))


def contrast_errors(primary: str, dark: str) -> dict[str, str]:
    """{champ: clé d'erreur} si un texte ne serait pas assez lisible (enregistrement bloqué).

    Avec du noir et du blanc purs, la couleur principale passe toujours (≥ 4.58:1 avec l'un
    des deux) : le contrôle reste là par sécurité. La couleur sombre doit porter du texte blanc.
    """
    errors = {}
    if contrast_ratio(primary, text_color_on(primary)) < MIN_CONTRAST:
        errors["color_primary"] = "error_branding_contrast_primary"
    if contrast_ratio(dark, WHITE) < MIN_CONTRAST:
        errors["color_dark"] = "error_branding_contrast_dark"
    return errors


# --- Saisie du formulaire ---

def clean_text(text: str) -> str:
    """Espaces en trop retirés, au début, à la fin et au milieu."""
    return " ".join(text.split())


def clean_color(text: str) -> str | None:
    """« #ff7900 » -> « #FF7900 » ; None si ce n'est pas exactement #RRGGBB."""
    color = text.strip().upper()
    return color if HEX_COLOR.fullmatch(color) else None


def parse_branding(form: dict[str, str]) -> tuple[Branding, dict[str, str]]:
    """Réglages saisis -> (Branding nettoyé, erreurs par champ : {champ: clé de traduction}).

    Le Branding renvoyé garde la saisie nettoyée (pour réafficher le formulaire) ;
    il ne faut l'enregistrer que s'il n'y a aucune erreur.
    """
    values, errors = {}, {}
    for name in FIELDS:
        text = form.get(name, "")
        if name.startswith("color_"):
            values[name] = clean_color(text) or text.strip()[:7]
            if clean_color(text) is None:
                errors[name] = "error_branding_color"
            continue
        values[name] = clean_text(text)
        is_tagline = name.startswith("tagline_")
        low, high = TAGLINE_LENGTH if is_tagline else NAME_LENGTH
        if FORBIDDEN_CHARACTERS & set(values[name]):
            errors[name] = "error_branding_characters"
        elif not low <= len(values[name]) <= high:
            errors[name] = "error_branding_length_tagline" if is_tagline else "error_branding_length"
    if not errors.keys() & {"color_primary", "color_dark"}:
        errors.update(contrast_errors(values["color_primary"], values["color_dark"]))
    return Branding(**values), errors


def changed_fields(before: Branding, after: Branding) -> list[tuple[str, str, str]]:
    """(champ, ancienne valeur, nouvelle valeur) pour chaque réglage modifié : l'historique."""
    return [(name, getattr(before, name), getattr(after, name))
            for name in FIELDS if getattr(before, name) != getattr(after, name)]


def split_tagline(tagline: str) -> tuple[str, str]:
    """Le héro visiteur affiche le slogan en deux morceaux, le second en couleur principale :
    « Pronostique les scores. » | « Défie tes amis. ». Coupé après la première phrase."""
    match = re.match(r"(.+?[.!?])\s+(.+)", tagline)
    return (match.group(1), match.group(2)) if match else (tagline, "")
