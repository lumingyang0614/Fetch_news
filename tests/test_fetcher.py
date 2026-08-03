from app.config import Settings, Stock
from app.fetcher import clean_html, mentions_stock, normalize_url


def test_normalize_url_removes_tracking() -> None:
    assert normalize_url("HTTPS://Example.com/a?utm_source=x&b=2&a=1#top") == "https://example.com/a?a=1&b=2"


def test_clean_html() -> None:
    assert clean_html("<p>Hello&nbsp; world</p>") == "Hello world"


def test_parse_stocks() -> None:
    settings = Settings(stocks="TW:2330:台積電,US:AAPL:Apple")
    assert [(s.market, s.symbol) for s in settings.stocks] == [("TW", "2330"), ("US", "AAPL")]


def test_database_url_uses_psycopg3() -> None:
    settings = Settings(database_url="postgresql://user:pass@localhost/news")
    assert settings.database_url == "postgresql+psycopg://user:pass@localhost/news"


def test_mentions_company_name_or_complete_symbol() -> None:
    stock = Stock("TW", "1301", "台塑")
    assert mentions_stock("台塑今日公布財報", stock)
    assert mentions_stock("1301 股價上漲", stock)
    assert not mentions_stock("編號 11301 與公司無關", stock)
    assert not mentions_stock("韓股與日經指數下跌", stock)


def test_short_us_symbol_requires_word_boundary() -> None:
    stock = Stock("US", "A", "Agilent Technologies")
    assert mentions_stock("A shares rise after earnings", stock)
    assert not mentions_stock("Apple shares rise", stock)
