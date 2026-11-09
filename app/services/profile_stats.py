"""Statistiques de la page Profil : réussite, forme, séries, compétitions, badges.

Fonctions pures : aucune base de données (les lectures sont dans profile_store.py).
"""
from dataclasses import dataclass, replace
from datetime import date, datetime

from app.services.ranking import PlayerScore, find_player, rank_players
from app.services.scoring import ScoringRules, score_prediction

EXACT, GOOD, MISS = "exact", "good", "miss"
FORM_SIZE = 10  # nombre de pronos affichés dans « Forme »
STRONG_MIN_PLAYED = 5  # pronos minimum pour la « compétition forte »


@dataclass(frozen=True)
class PlayedPick:
    """Un prono sur un match terminé."""

    pred_home: int
    pred_away: int
    real_home: int
    real_away: int
    kickoff_at: datetime
    competition: str
    competition_id: int = 0
    points: int = 0  # points calculés (0 si pas encore calculés)
    matchday: int | None = None  # numéro de journée du fournisseur, s'il le donne


@dataclass(frozen=True)
class Summary:
    played: int
    exacts: int
    goods: int  # bons résultats sans score exact
    misses: int
    success_rate: int  # en %, arrondi à l'entier
    exact_pct: int  # répartition : les 3 font 100 (tous à 0 si aucun prono)
    good_pct: int
    miss_pct: int
    points: int
    average_points: float  # points par prono joué


@dataclass(frozen=True)
class CompetitionStat:
    name: str
    played: int
    success_rate: int


def pick_outcome(pick: PlayedPick) -> str:
    """Score exact, bon résultat (bon vainqueur ou bon nul) ou raté."""
    result = score_prediction(pick.pred_home, pick.pred_away, pick.real_home, pick.real_away,
                              ScoringRules())
    if result.is_exact:
        return EXACT
    return GOOD if result.is_winner else MISS


def percent(part: int, total: int) -> int:
    """Pourcentage arrondi à l'entier le plus proche (0,5 vers le haut) ; 0 si total nul."""
    return (200 * part + total) // (2 * total) if total else 0


def summarize(picks: list[PlayedPick]) -> Summary:
    outcomes = [pick_outcome(pick) for pick in picks]
    played = len(outcomes)
    exacts, goods = outcomes.count(EXACT), outcomes.count(GOOD)
    misses = played - exacts - goods
    rate = percent(exacts + goods, played)
    # Répartition calée sur le taux de réussite : exact + bon résultat = réussite
    exact_pct = min(percent(exacts, played), rate)
    points = sum(pick.points for pick in picks)
    return Summary(played=played, exacts=exacts, goods=goods, misses=misses,
                   success_rate=rate, exact_pct=exact_pct, good_pct=rate - exact_pct,
                   miss_pct=100 - rate if played else 0,
                   points=points, average_points=round(points / played, 1) if played else 0.0)


def chronological_outcomes(picks: list[PlayedPick]) -> list[str]:
    return [pick_outcome(pick) for pick in sorted(picks, key=lambda pick: pick.kickoff_at)]


def recent_form(outcomes: list[str], size: int = FORM_SIZE) -> list[str]:
    """Les `size` derniers résultats, du plus ancien au plus récent."""
    return outcomes[-size:]


def current_streak(outcomes: list[str]) -> int:
    """Pronos réussis (exact ou bon résultat) d'affilée, en finissant par le plus récent."""
    streak = 0
    for outcome in reversed(outcomes):
        if outcome == MISS:
            break
        streak += 1
    return streak


def best_streak(outcomes: list[str]) -> int:
    best = streak = 0
    for outcome in outcomes:
        streak = 0 if outcome == MISS else streak + 1
        best = max(best, streak)
    return best


def by_competition(picks: list[PlayedPick]) -> list[CompetitionStat]:
    """Une ligne par compétition jouée, la plus jouée d'abord."""
    names = sorted({pick.competition for pick in picks})
    stats = []
    for name in names:
        summary = summarize([pick for pick in picks if pick.competition == name])
        stats.append(CompetitionStat(name, summary.played, summary.success_rate))
    return sorted(stats, key=lambda stat: (-stat.played, stat.name))


def strongest_competition(stats: list[CompetitionStat],
                          min_played: int = STRONG_MIN_PLAYED) -> CompetitionStat | None:
    """Meilleur taux de réussite parmi les compétitions d'au moins `min_played` pronos."""
    eligible = [stat for stat in stats if stat.played >= min_played]
    return max(eligible, key=lambda stat: (stat.success_rate, stat.played), default=None)


# --- Évolution dans un classement, journée par journée ---

@dataclass(frozen=True)
class DayScore:
    """Résultat d'un prono calculé, avec le jour (UTC) du coup d'envoi."""

    player: PlayerScore  # identité du joueur + points, exact (0/1), bon vainqueur (0/1)
    day: date


def best_daily_climb(day_scores: list[DayScore], user_id: int) -> int:
    """Le plus grand nombre de places gagnées par le joueur en une journée où il a joué.

    Rang avant la journée comparé au rang après ; il faut être déjà classé avant.
    """
    by_day: dict[date, list[PlayerScore]] = {}
    for score in day_scores:
        by_day.setdefault(score.day, []).append(score.player)

    totals: dict[int, PlayerScore] = {}
    best = 0
    for day in sorted(by_day):
        before = find_player(rank_players(list(totals.values())), user_id)
        for player in by_day[day]:
            totals[player.user_id] = _add(totals.get(player.user_id), player)
        played_today = any(player.user_id == user_id for player in by_day[day])
        if before and played_today:
            after = find_player(rank_players(list(totals.values())), user_id)
            best = max(best, before.rank - after.rank)
    return best


def _add(total: PlayerScore | None, day: PlayerScore) -> PlayerScore:
    if total is None:
        return day
    return replace(total, points=total.points + day.points, exacts=total.exacts + day.exacts,
                   winners=total.winners + day.winners)


# --- Badges (calculés à la volée) ---

@dataclass(frozen=True)
class Badge:
    key: str  # sert aussi aux clés de traduction badge_<key> et badge_<key>_rule
    icon: str
    remaining: int  # ce qu'il manque pour le débloquer (0 = débloqué)

    @property
    def unlocked(self) -> bool:
        return self.remaining == 0


BADGE_GOALS = {"prophet": 3, "remontada": 5, "gatherer": 1, "flawless": 5}


def compute_badges(exacts: int, best_climb: int, invited_friends: int,
                   best_success_streak: int) -> list[Badge]:
    """Prophète : 3 scores exacts. Remontada : +5 places en une journée.
    Rassembleur : au moins un ami entré dans une ligue grâce à mon lien d'invitation.
    Sans faute : 5 pronos réussis d'affilée."""
    progress = {"prophet": exacts, "remontada": best_climb, "gatherer": invited_friends,
                "flawless": best_success_streak}
    icons = {"prophet": "eye", "remontada": "trend", "gatherer": "people", "flawless": "shield"}
    return [Badge(key, icons[key], max(goal - progress[key], 0))
            for key, goal in BADGE_GOALS.items()]


def next_badge(badges: list[Badge]) -> Badge | None:
    """Le badge verrouillé le plus proche (le moins de choses à faire)."""
    locked = [badge for badge in badges if not badge.unlocked]
    return min(locked, key=lambda badge: badge.remaining, default=None)


def single_matchday(picks: list[PlayedPick]) -> int | None:
    """Numéro de journée commun à tous ces pronos (ex. la semaine), sinon None.

    None aussi si un match n'a pas de journée (coupe, match ajouté à la main)
    ou si la semaine mélange plusieurs journées (plusieurs compétitions).
    """
    matchdays = {pick.matchday for pick in picks}
    return matchdays.pop() if len(matchdays) == 1 and None not in matchdays else None


def choose_competition(competitions: list[tuple[int, str]], wanted: str | None) -> int | None:
    """Compétition du filtre « Compét. » : celle demandée, sinon la Ligue des champions,
    sinon la première. `competitions` : (id, nom) des compétitions actives."""
    ids = [competition_id for competition_id, _ in competitions]
    if wanted and wanted.isdigit() and int(wanted) in ids:
        return int(wanted)
    champions = [competition_id for competition_id, name in competitions
                 if "champions" in name.lower()]
    return (champions or ids or [None])[0]


def rank_change(before: PlayerScore | None, now: PlayerScore | None) -> int | None:
    """Places gagnées (positif) ou perdues (négatif) ; None si pas classé avant ou maintenant."""
    if before is None or now is None:
        return None
    return before.rank - now.rank
