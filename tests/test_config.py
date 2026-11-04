from app.config import DEFAULT_DATABASE_URL, load_settings, normalize_database_url


def test_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert load_settings().database_url == DEFAULT_DATABASE_URL


def test_database_url_read_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./other.db")
    assert load_settings().database_url == "sqlite:///./other.db"


def test_render_postgres_urls_use_psycopg_driver():
    expected = "postgresql+psycopg://user:pw@host/db"
    assert normalize_database_url("postgres://user:pw@host/db") == expected
    assert normalize_database_url("postgresql://user:pw@host/db") == expected


def test_other_urls_are_unchanged():
    assert normalize_database_url("sqlite:///./x.db") == "sqlite:///./x.db"
    assert normalize_database_url("postgresql+psycopg://h/db") == "postgresql+psycopg://h/db"


def test_secure_cookies_off_by_default(monkeypatch):
    monkeypatch.delenv("SECURE_COOKIES", raising=False)
    assert load_settings().secure_cookies is False


def test_secure_cookies_enabled_from_env(monkeypatch):
    monkeypatch.setenv("SECURE_COOKIES", "true")
    assert load_settings().secure_cookies is True


def test_sync_token_empty_by_default(monkeypatch):
    monkeypatch.delenv("SYNC_TOKEN", raising=False)
    assert load_settings().sync_token == ""


def test_data_provider_defaults_to_football_data(monkeypatch):
    monkeypatch.delenv("DATA_PROVIDER", raising=False)
    assert load_settings().data_provider == "football_data"
