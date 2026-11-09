"""Configuration Jinja2 partagée par toutes les routes."""
import hashlib
from functools import cache
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.i18n import (closing_when, current_language, format_date_time, format_day, format_rank,
                      format_time, time_ago, translate)
from app.i18n.countries import country_name, country_options
from app.services.avatars import initials
from app.services.leagues import format_code
from app.services.score_colors import score_classes
from app.services.teams import team_initials


STATIC_DIR = Path(__file__).parent / "static"


def static_url(path: str) -> str:
    """« /static/css/style.css?v=1a2b3c4d » : la version change avec le contenu du fichier,
    le navigateur peut donc le garder un an en cache (voir CachedStaticFiles)."""
    return _versioned_url(path, (STATIC_DIR / path).stat().st_mtime)


@cache
def _versioned_url(path: str, modified_at: float) -> str:
    # Recalculé seulement quand le fichier change (date de modification)
    digest = hashlib.md5((STATIC_DIR / path).read_bytes()).hexdigest()[:8]
    return f"/static/{path}?v={digest}"


def language_context(request) -> dict:
    """Langue de la requête (posée par le middleware de app/main.py) pour tous les templates."""
    return {"lang": current_language()}


templates = Jinja2Templates(directory=Path(__file__).parent / "templates",
                            context_processors=[language_context])
templates.env.globals["t"] = translate
templates.env.globals["static_url"] = static_url
templates.env.globals["country_options"] = country_options
templates.env.globals["country_name"] = country_name
templates.env.globals["format_day"] = format_day
templates.env.globals["format_time"] = format_time
templates.env.globals["format_date_time"] = format_date_time
templates.env.globals["score_classes"] = score_classes
templates.env.globals["closing_when"] = closing_when
templates.env.globals["initials"] = initials
templates.env.globals["team_initials"] = team_initials
templates.env.globals["time_ago"] = time_ago
templates.env.globals["format_rank"] = format_rank
templates.env.globals["format_code"] = format_code
