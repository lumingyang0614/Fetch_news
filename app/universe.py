from __future__ import annotations

import csv
import io
import json
import logging
from urllib.request import Request, urlopen

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, Stock
from app.models import Company

logger = logging.getLogger(__name__)
SOURCES = {
    "TWSE": "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
    "TPEX": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
    "TPEX_EMERGING": "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R",
    "NASDAQ": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "OTHER_US": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}


def download(url: str, settings: Settings) -> bytes:
    request = Request(url, headers={"User-Agent": settings.user_agent})
    with urlopen(request, timeout=settings.request_timeout_seconds) as response:
        return response.read()


def parse_tw(data: bytes, exchange: str) -> list[dict]:
    rows = json.loads(data.decode("utf-8-sig"))
    result = []
    for row in rows:
        # TWSE currently uses Chinese field names, while TPEx uses English
        # OpenAPI field names. Keep both formats supported.
        symbol = str(row.get("公司代號") or row.get("SecuritiesCompanyCode") or "").strip()
        name = str(
            row.get("公司簡稱")
            or row.get("公司名稱")
            or row.get("CompanyAbbreviation")
            or row.get("CompanyName")
            or ""
        ).strip()[:200]
        if symbol and name:
            result.append({"market": "TW", "symbol": symbol, "name": name, "exchange": exchange, "enabled": True})
    return result


def parse_us(data: bytes, exchange: str) -> list[dict]:
    text = data.decode("utf-8-sig", errors="replace")
    rows = csv.DictReader(io.StringIO(text), delimiter="|")
    result = []
    for row in rows:
        symbol = (row.get("Symbol") or row.get("ACT Symbol") or "").strip()
        # A single overlong Nasdaq description must not roll back the whole
        # exchange import; Company.name is stored as VARCHAR(200).
        name = (row.get("Security Name") or "").strip()[:200]
        if not symbol or not name or symbol.startswith("File Creation Time"):
            continue
        if row.get("Test Issue", "N") == "Y" or row.get("ETF", "N") == "Y":
            continue
        result.append({"market": "US", "symbol": symbol, "name": name, "exchange": exchange, "enabled": True})
    return result


def upsert_companies(session: Session, companies: list[dict]) -> int:
    if not companies:
        return 0
    statement = insert(Company).values(companies)
    statement = statement.on_conflict_do_update(
        index_elements=["market", "symbol"],
        set_={"name": statement.excluded.name, "exchange": statement.excluded.exchange},
    )
    session.execute(statement)
    session.commit()
    return len(companies)


def sync_universe(settings: Settings, sessions: sessionmaker[Session]) -> int:
    total = 0
    with sessions() as session:
        custom = [
            {"market": s.market, "symbol": s.symbol, "name": s.name, "exchange": "CUSTOM", "enabled": True}
            for s in settings.stocks
        ]
        total += upsert_companies(session, custom)
        loaders = [
            ("TWSE", parse_tw),
            ("TPEX", parse_tw),
            ("TPEX_EMERGING", parse_tw),
            ("NASDAQ", parse_us),
            ("OTHER_US", parse_us),
        ]
        for source, parser in loaders:
            try:
                count = upsert_companies(session, parser(download(SOURCES[source], settings), source))
                total += count
                logger.info("%s 股票池同步 %d 檔", source, count)
            except Exception:
                session.rollback()
                logger.exception("%s 股票池同步失敗", source)
    logger.info("股票池同步完成，共處理 %d 檔", total)
    return total
