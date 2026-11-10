"""Statistiques de la page Profil : réussite, forme, séries, compétitions, badges.

Fonctions pures : aucune base de données (les lectures sont dans profile_store.py).
"""
from dataclasses import dataclass
from datetime import date, datetime

from app.services.ranking import PlayerScore
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


def stable_competition_rows(period: list[CompetitionStat],
                            career: list[CompetitionStat]) -> list[CompetitionStat]:
    """Mêmes lignes « Par compétition » pour tous les filtres (la page ne bouge pas) :
    les compétitions de toute la carrière, dans le même ordre, avec les chiffres de la
    période (0 si aucun prono sur la période)."""
    in_period = {stat.name: stat for stat in period}
    return [in_period.get(stat.name, CompetitionStat(stat.name, 0, 0)) for stat in career]


def strongest_competition(stats: list[CompetitionStat],
                          min_played: int = STRONG_MIN_PLAYED) -> CompetitionStat | None:
    """Meilleur taux de réussite parmi les compétitions d'au moins `min_played` pronos."""
    eligible = [stat for stat in stats if stat.played >= min_played]
    return max(eligible, key=lambda stat: (stat.success_rate, stat.played), default=None)


# --- Évolution au classement général, journée par journée ---

def best_climb(ranks: list[tuple[date, int]], played_days: set[date]) -> int:
    """Le plus grand nombre de places gagnées en une journée où le joueur a joué.

    `ranks` : (jour, rang) tirés de l'historique des rangs ; on compare le rang
    du jour à celui de la journée précédente où le joueur était classé.
    """
    best, previous = 0, None
    for day, rank in sorted(ranks):
        if previous is not None and day in played_days:
            best = max(best, previous - rank)
        previous = rank
    return best


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
