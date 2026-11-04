"""Règles des ligues privées (SPEC §6). Fonctions pures : aucune base.

Les erreurs sont des clés de traduction, ou None si tout va bien.
"""
import re
import secrets

MAX_MEMBERS = 100  # paramétrable par l'admin global plus tard (back-office, étape 8)
MAX_LEAGUES_PER_PLAYER = 10
NAME_MIN, NAME_MAX = 3, 40

# Sans caractères qui se confondent à l'écrit ou à l'oral : 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def generate_code() -> str:
    """Code d'invitation aléatoire, ex. « K7PM4X »."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(text: str) -> str:
    """Code tapé par un joueur : « k7p m4x » ou « K7P-M4X » -> « K7PM4X »."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def clean_name(name: str) -> str:
    """Espaces superflus retirés."""
    return " ".join(name.split())


def validate_league_name(name: str) -> str | None:
    if not NAME_MIN <= len(clean_name(name)) <= NAME_MAX:
        return "error_league_name"
    return None


def create_error(player_league_count: int) -> str | None:
    if player_league_count >= MAX_LEAGUES_PER_PLAYER:
        return "error_too_many_leagues"
    return None


def join_error(is_member: bool, member_count: int, player_league_count: int) -> str | None:
    """Pourquoi le joueur ne peut pas rejoindre la ligue, ou None s'il le peut."""
    if is_member:
        return "error_already_member"
    if member_count >= MAX_MEMBERS:
        return "error_league_full"
    return create_error(player_league_count)


def leave_error(is_owner: bool) -> str | None:
    """L'admin ne quitte pas sa ligue : il la supprime."""
    return "error_owner_cannot_leave" if is_owner else None


def remove_error(is_owner: bool, target_is_owner: bool) -> str | None:
    """Seul l'admin retire un membre, et pas lui-même."""
    if not is_owner:
        return "error_not_league_owner"
    if target_is_owner:
        return "error_owner_cannot_leave"
    return None
