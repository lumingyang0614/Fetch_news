from __future__ import annotations

import hashlib
import logging
import re
from calendar import timegm
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import feedparser
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, Stock
from app.models import Company, CompanyNews

logger = logging.getLogger(__name__)
TRACKING_PARAMS = {"gclid", "fbclid", "ref", "source"}


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
        )
    )
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, query, ""))


def clean_html(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def google_news_url(stock: Stock, lookback_days: int) -> str:
    market_hint = "台股 OR 上市 OR 櫃買" if stock.market == "TW" else "stock OR NASDAQ OR NYSE"
    query = quote_plus(f'("{stock.name}" OR "{stock.symbol}") ({market_hint}) when:{lookback_days}d')
    if stock.market == "TW":
        return f"https://news.google.com/rss/search?q={query}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


def entry_datetime(entry: dict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.fromtimestamp(timegm(parsed), tz=timezone.utc) if parsed else None


def fetch_stock(stock: Stock, settings: Settings) -> list[dict]:
    request = Request(google_news_url(stock, settings.news_lookback_days), headers={"User-Agent": settings.user_agent})
    with urlopen(request, timeout=settings.request_timeout_seconds) as response:
        feed = feedparser.parse(response.read())
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.news_lookback_days)
    items = []
    for entry in feed.entries:
        published_at = entry_datetime(entry)
        if published_at and published_at < cutoff:
            continue
        url = normalize_url(entry.get("link", ""))
        if not url:
            continue
        source = entry.get("source", {})
        items.append(
            {
                "market": stock.market,
                "symbol": stock.symbol,
                "company_name": stock.name,
                "title": clean_html(entry.get("title")) or "(無標題)",
                "summary": clean_html(entry.get("summary")),
                "source": source.get("title") if isinstance(source, dict) else None,
                "url": url,
                "url_hash": hashlib.sha256(url.encode()).hexdigest(),
                "published_at": published_at,
            }
        )
    return items


def save_items(session: Session, items: list[dict]) -> int:
    if not items:
        return 0
    statement = insert(CompanyNews).values(items).on_conflict_do_nothing(
        index_elements=["market", "symbol", "url_hash"]
    )
    result = session.execute(statement)
    session.commit()
    return result.rowcount


def prune_old_news(session: Session, keep_per_stock: int) -> int:
    result = session.execute(
        text(
            """
            WITH ranked AS (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY market, symbol
                           ORDER BY COALESCE(published_at, fetched_at) DESC, id DESC
                       ) AS position
                FROM company_news
            )
            DELETE FROM company_news AS news
            USING ranked
            WHERE news.id = ranked.id
              AND ranked.position > :keep_per_stock
            """
        ),
        {"keep_per_stock": keep_per_stock},
    )
    session.commit()
    return result.rowcount


def fetch_all(settings: Settings, sessions: sessionmaker[Session]) -> tuple[int, int]:
    found = inserted = 0
    with sessions() as session:
        companies = session.scalars(
            select(Company)
            .where(Company.enabled.is_(True))
            .order_by(Company.last_fetched_at.asc().nullsfirst(), Company.id)
            .limit(settings.fetch_batch_size)
        ).all()
        for company in companies:
            stock = Stock(company.market, company.symbol, company.name)
            try:
                items = fetch_stock(stock, settings)
                found += len(items)
                count = save_items(session, items)
                inserted += count
                company.last_fetched_at = datetime.now(timezone.utc)
                session.commit()
                logger.info("%s:%s 找到 %d 則，新增 %d 則", stock.market, stock.symbol, len(items), count)
            except Exception:
                session.rollback()
                logger.exception("擷取 %s:%s 失敗", stock.market, stock.symbol)
        deleted = prune_old_news(session, settings.max_news_per_stock)
        logger.info("資料保留清理：刪除 %d 則舊新聞，每檔保留最新 %d 則", deleted, settings.max_news_per_stock)
    logger.info("本輪完成：找到 %d 則，新增 %d 則", found, inserted)
    return found, inserted
