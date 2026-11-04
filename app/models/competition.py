from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Competition(Base):
    __tablename__ = "competitions"
    __table_args__ = (UniqueConstraint("provider", "external_id",
                                       name="uq_competitions_provider_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))  # voir app/providers/__init__.py
    external_id: Mapped[str] = mapped_column(String(40))  # identifiant chez le fournisseur
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), default="")
    logo_url: Mapped[str] = mapped_column(String(255), default="")
    season: Mapped[int | None] = mapped_column(Integer)  # saison en cours, ex. 2026
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # choisie par l'admin
