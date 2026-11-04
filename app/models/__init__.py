"""Tables de la base. Importer ici chaque modèle pour qu'Alembic le détecte."""
from app.db import Base  # noqa: F401
from app.models.api_call_log import ApiCallLog  # noqa: F401
from app.models.competition import Competition  # noqa: F401
from app.models.match import Match, MatchStatus  # noqa: F401
