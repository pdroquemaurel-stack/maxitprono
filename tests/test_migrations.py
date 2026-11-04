"""Migrations Alembic appliquées sur une vraie base SQLite (fichier temporaire)."""
import dataclasses

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

import app.config

BEFORE_PROVIDERS = "abe340e3b4d5"


@pytest.fixture
def alembic_config(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    # migrations/env.py lit l'URL dans les réglages de l'app
    monkeypatch.setattr(app.config, "settings",
                        dataclasses.replace(app.config.settings, database_url=url))
    config = Config("alembic.ini")
    config.attributes["url"] = url
    return config


def test_providers_migration_keeps_existing_data(alembic_config):
    command.upgrade(alembic_config, BEFORE_PROVIDERS)
    engine = create_engine(alembic_config.attributes["url"])
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO competitions (id, api_id, name, country, logo_url, is_active)"
                          " VALUES (1, 61, 'Ligue 1', 'France', '', 1),"
                          " (2, 999999, 'Démo', 'World', '', 1)"))
        conn.execute(text("INSERT INTO matches (id, api_id, competition_id, home_team, away_team,"
                          " home_logo_url, away_logo_url, kickoff_at, status) VALUES"
                          " (1, 1001, 1, 'A', 'B', '', '', '2026-11-10 19:00:00', 'scheduled'),"
                          " (2, NULL, 2, 'C', 'D', '', '', '2026-11-10 19:00:00', 'scheduled')"))

    command.upgrade(alembic_config, "head")

    with engine.connect() as conn:
        competitions = conn.execute(text(
            "SELECT provider, external_id FROM competitions ORDER BY id")).all()
        matches = conn.execute(text("SELECT provider, external_id FROM matches ORDER BY id")).all()
    assert competitions == [("api_football", "61"), ("demo", "demo")]
    assert matches == [("api_football", "1001"), (None, None)]


def test_migrations_go_down_and_up_again(alembic_config):
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, BEFORE_PROVIDERS)
    command.upgrade(alembic_config, "head")
