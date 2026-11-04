"""Configuration Jinja2 partagée par toutes les routes."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings
from app.i18n import translate
from app.i18n.countries import country_name, country_options

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["t"] = translate
templates.env.globals["lang"] = settings.default_language
templates.env.globals["country_options"] = country_options
templates.env.globals["country_name"] = country_name
