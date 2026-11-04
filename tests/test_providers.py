import dataclasses

import pytest

import app.config
from app.providers import make_provider
from app.providers.api_football import ApiFootballClient
from app.providers.base import ProviderError
from app.providers.football_data import FootballDataClient


def use_settings(monkeypatch, **values):
    monkeypatch.setattr(app.config, "settings", dataclasses.replace(app.config.settings, **values))


def test_football_data_is_chosen(db, monkeypatch):
    use_settings(monkeypatch, data_provider="football_data", football_data_api_key="k")
    provider = make_provider(db)
    assert isinstance(provider, FootballDataClient)
    assert provider.name == "football_data"


def test_api_football_is_chosen(db, monkeypatch):
    use_settings(monkeypatch, data_provider="api_football", api_football_key="k")
    assert isinstance(make_provider(db), ApiFootballClient)


def test_unknown_provider_is_refused(db, monkeypatch):
    use_settings(monkeypatch, data_provider="other")
    with pytest.raises(ProviderError, match="DATA_PROVIDER inconnu"):
        make_provider(db)
