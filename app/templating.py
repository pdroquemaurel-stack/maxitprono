"""Configuration Jinja2 partagée par toutes les routes."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.i18n import translate

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["t"] = translate
templates.env.globals["lang"] = settings.default_language
