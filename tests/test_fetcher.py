from app.config import Settings
from app.fetcher import clean_html, normalize_url


def test_normalize_url_removes_tracking() -> None:
    assert normalize_url("HTTPS://Example.com/a?utm_source=x&b=2&a=1#top") == "https://example.com/a?a=1&b=2"


def test_clean_html() -> None:
    assert clean_html("<p>Hello&nbsp; world</p>") == "Hello world"


def test_parse_stocks() -> None:
    settings = Settings(STOCKS="TW:2330:台積電,US:AAPL:Apple")
    assert [(s.market, s.symbol) for s in settings.stocks] == [("TW", "2330"), ("US", "AAPL")]


def test_database_url_uses_psycopg3() -> None:
    settings = Settings(DATABASE_URL="postgresql://user:pass@localhost/news")
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost/news"
