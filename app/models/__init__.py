"""Tables de la base. Importer ici chaque modèle pour qu'Alembic le détecte."""
from app.db import Base  # noqa: F401
from app.models.api_call_log import ApiCallLog  # noqa: F401
from app.models.competition import Competition  # noqa: F401
from app.models.match import Match, MatchStatus  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.league import League, LeagueMember  # noqa: F401
from app.models.game_settings import GameSettings  # noqa: F401
from app.models.rank_snapshot import RankSnapshot  # noqa: F401
