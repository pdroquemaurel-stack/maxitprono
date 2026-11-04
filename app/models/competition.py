from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_id: Mapped[int] = mapped_column(Integer, unique=True)  # identifiant API-Football
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="")
    logo_url: Mapped[str] = mapped_column(String(255), default="")
    season: Mapped[int | None] = mapped_column(Integer)  # saison en cours, ex. 2026
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # choisie par l'admin
