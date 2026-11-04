from app.config import DEFAULT_DATABASE_URL, load_settings


def test_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load_settings().database_url == DEFAULT_DATABASE_URL


def test_database_url_read_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    assert load_settings().database_url == "sqlite:///./other.db"
