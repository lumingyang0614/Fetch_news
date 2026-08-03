from app.universe import parse_us, parse_tw


def test_parse_tw() -> None:
    data = '[{"公司代號":"2330","公司簡稱":"台積電"}]'.encode()
    assert parse_tw(data, "TWSE")[0]["symbol"] == "2330"


def test_parse_emerging_stock_keeps_exchange() -> None:
    data = '[{"公司代號":"7777","公司簡稱":"測試興櫃"}]'.encode()
    company = parse_tw(data, "TPEX_EMERGING")[0]
    assert company["market"] == "TW"
    assert company["exchange"] == "TPEX_EMERGING"


def test_parse_us_excludes_etf_and_test() -> None:
    data = b"Symbol|Security Name|ETF|Test Issue\nAAPL|Apple Inc. Common Stock|N|N\nQQQ|ETF|Y|N\nFile Creation Time: x|||\n"
    assert [row["symbol"] for row in parse_us(data, "NASDAQ")] == ["AAPL"]
