from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.types import UTCDateTime, utc_now


class BrandingRow(Base):
    """Personnalisation (nom, logo, couleurs) : une seule ligne (id = 1).

    Pas de ligne = valeurs par défaut (app/services/branding.py).
    """

    __tablename__ = "branding"

    id: Mapped[int] = mapped_column(primary_key=True)
    app_name: Mapped[str] = mapped_column(String(30))
    logo_part1: Mapped[str] = mapped_column(String(30))
    logo_part2: Mapped[str] = mapped_column(String(30))
    publisher_name: Mapped[str] = mapped_column(String(30))
    tagline_fr: Mapped[str] = mapped_column(String(60))
    tagline_en: Mapped[str] = mapped_column(String(60))
    color_primary: Mapped[str] = mapped_column(String(7))
    color_dark: Mapped[str] = mapped_column(String(7))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class BrandingChange(Base):
    """Historique : qui a modifié quel réglage de personnalisation, et quand."""

    __tablename__ = "branding_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    field: Mapped[str] = mapped_column(String(30))
    old_value: Mapped[str] = mapped_column(String(60))
    new_value: Mapped[str] = mapped_column(String(60))
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now, index=True)
