"""Règles des ligues privées (SPEC §6). Fonctions pures : aucune base.

Les erreurs sont des clés de traduction, ou None si tout va bien.
"""
import re
import secrets

from app.services.probabilities import round_to_100
from app.services.ranking import PlayerScore

MAX_LEAGUES_PER_PLAYER = 10
NAME_MIN, NAME_MAX = 3, 30

# Couleurs proposées pour l'icône de la ligue ; la première est celle par défaut
LEAGUE_COLORS = ("orange", "black", "green", "peach")

# Sans caractères qui se confondent à l'écrit ou à l'oral : 0/O, 1/I/L
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def generate_code() -> str:
    """Code d'invitation aléatoire, ex. « K7PM4X »."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def format_code(code: str) -> str:
    """Code affiché en deux groupes, plus facile à lire et à dicter : « K7PM4X » -> « K7P-M4X »."""
    middle = len(code) // 2
    return f"{code[:middle]}-{code[middle:]}" if len(code) > 3 else code


def normalize_code(text: str) -> str:
    """Code tapé par un joueur : « k7p m4x » ou « K7P-M4X » -> « K7PM4X »."""
    return re.sub(r"[^A-Z0-9]", "", text.upper())


def clean_name(name: str) -> str:
    """Espaces superflus retirés."""
    return " ".join(name.split())


def validate_league_name(name: str, current_name: str | None = None) -> str | None:
    """`current_name` : nom actuel de la ligue. Il reste accepté tel quel, même hors des
    limites : les ligues créées avant le 9 novembre 2026 pouvaient avoir 40 caractères."""
    if current_name is not None and clean_name(name) == clean_name(current_name):
        return None
    if not NAME_MIN <= len(clean_name(name)) <= NAME_MAX:
        return "error_league_name"
    return None


def clean_color(color: str) -> str:
    """Couleur choisie si elle fait partie de la palette, sinon la couleur par défaut."""
    return color if color in LEAGUE_COLORS else LEAGUE_COLORS[0]


def clean_competition_ids(values: list[str], available_ids: set[int]) -> list[int]:
    """Compétitions cochées, parmi celles proposées. Liste vide = toutes (« Toutes » cochée
    ou rien de coché)."""
    if "all" in values:
        return []
    return sorted({int(v) for v in values if v.isdigit() and int(v) in available_ids})


def create_error(player_league_count: int) -> str | None:
    if player_league_count >= MAX_LEAGUES_PER_PLAYER:
        return "error_too_many_leagues"
    return None


def join_error(is_member: bool, member_count: int, player_league_count: int,
               max_members: int) -> str | None:
    """Pourquoi le joueur ne peut pas rejoindre la ligue, ou None s'il le peut.

    `max_members` : taille maximale réglée par l'admin (back-office).
    """
    if is_member:
        return "error_already_member"
    if member_count >= max_members:
        return "error_league_full"
    return create_error(player_league_count)


def valid_inviter(ref: str | None, member_ids: list[int], joiner_id: int) -> int | None:
    """Identifiant du parrain (?ref= du lien) s'il est membre de la ligue et n'est pas
    le joueur lui-même ; sinon None (lien bricolé ou parrain parti)."""
    if not ref or not ref.isdigit():
        return None
    inviter_id = int(ref)
    return inviter_id if inviter_id in member_ids and inviter_id != joiner_id else None


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


def invite_from_next(next_url: str) -> tuple[str, str | None] | None:
    """(code, parrain) si l'adresse de retour après connexion est un lien d'invitation
    « /join/CODE?ref=12 », sinon None."""
    path, _, query = next_url.partition("?")
    match = re.fullmatch(r"/(?:join|j)/([A-Za-z0-9-]+)", path)
    if match is None:
        return None
    ref = next((part[4:] for part in query.split("&") if part.startswith("ref=")), None)
    return match.group(1), ref


def pick_league(league_ids: list[int], wanted: str | None) -> int | None:
    """Ligue à afficher : celle demandée si le joueur en est membre, sinon la première."""
    if wanted and wanted.isdigit() and int(wanted) in league_ids:
        return int(wanted)
    return league_ids[0] if league_ids else None


def sort_league_predictions(rows: list[tuple], me_id: int | None) -> list[tuple]:
    """Pronos de la ligue sur un match : moi d'abord, puis par points, sans prono en dernier.

    `rows` : (user_id, pseudo, pronostic ou None).
    """
    def key(row):
        user_id, nickname, prediction = row
        points = prediction.points if prediction is not None and prediction.points is not None else -1
        return (user_id != me_id, prediction is None, -points, nickname.lower())
    return sorted(rows, key=key)


# --- Écran d'une ligue : calculs simples sur les classements ---

def rank_moves(before: list[PlayerScore], now: list[PlayerScore]) -> dict[int, int | None]:
    """Places gagnées (positif) ou perdues (négatif) par joueur depuis le classement `before`.

    None : le joueur n'était pas encore classé avant (nouvel entrant).
    """
    before_ranks = {player.user_id: player.rank for player in before}
    return {player.user_id: (before_ranks[player.user_id] - player.rank
                             if player.user_id in before_ranks else None)
            for player in now}


def standings(ranking: list[PlayerScore], members: list[tuple[int, str]]) -> list[PlayerScore]:
    """Classement complet de la ligue : les joueurs classés, puis les membres qui n'ont
    encore aucun point compté (rang 0, par pseudo). `members` : (user_id, pseudo)."""
    ranked_ids = {player.user_id for player in ranking}
    waiting = sorted((m for m in members if m[0] not in ranked_ids), key=lambda m: m[1].lower())
    return ranking + [PlayerScore(user_id, nickname, "", None, 0, 0, 0, rank=0)
                      for user_id, nickname in waiting]


def week_extremes(week_ranking: list[PlayerScore]) -> tuple[PlayerScore | None, PlayerScore | None]:
    """Joueur de la semaine (le plus de points) et lanterne rouge (le moins).

    Il faut au moins deux joueurs ayant joué pour désigner une lanterne rouge.
    """
    if not week_ranking:
        return None, None
    return week_ranking[0], (week_ranking[-1] if len(week_ranking) >= 2 else None)


def league_trend(scores: list[tuple[int, int]]) -> tuple[int, int, int] | None:
    """Part des pronos victoire domicile / nul / victoire extérieur (somme = 100).

    On ne renvoie que la tendance : jamais les scores eux-mêmes avant le coup d'envoi.
    """
    if not scores:
        return None
    home = sum(1 for h, a in scores if h > a)
    draw = sum(1 for h, a in scores if h == a)
    return tuple(round_to_100([home, draw, len(scores) - home - draw]))


def gap_to_leader(ranking: list[PlayerScore], me: PlayerScore | None) -> int | None:
    """Points de retard sur le 1er (0 si je suis 1er), None si je ne suis pas classé."""
    if me is None or not ranking:
        return None
    return ranking[0].points - me.points


def ranking_preview(rest: list[PlayerScore], me_id: int, limit: int) -> list[PlayerScore]:
    """Lignes affichées sous le podium : les `limit` premières, plus la mienne si elle est
    plus bas (le classement complet est sur « Voir les N membres »)."""
    shown = rest[:limit]
    mine = next((row for row in rest[limit:] if row.user_id == me_id), None)
    return shown + ([mine] if mine else [])
