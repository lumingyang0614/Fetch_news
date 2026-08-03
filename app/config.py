from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


@dataclass(frozen=True)
class Stock:
    market: str
    symbol: str
    name: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/news"
    fetch_interval_minutes: int = Field(default=30, ge=1)
    fetch_on_start: bool = True
    fetch_batch_size: int = Field(default=100, ge=1, le=1000)
    max_news_per_stock: int = Field(default=20, ge=1, le=10000)
    auto_sync_universe: bool = True
    universe_sync_hour: int = Field(default=3, ge=0, le=23)
    news_lookback_days: int = Field(default=7, ge=1, le=30)
    request_timeout_seconds: int = Field(default=20, ge=1, le=120)
    user_agent: str = "company-news-fetcher/1.0"
    stocks: Annotated[list[Stock], NoDecode] = [
        Stock("TW", "2330", "台積電"),
        Stock("US", "AAPL", "Apple"),
    ]

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg3_driver(cls, value: object) -> object:
        """讓常見的 PostgreSQL URL 自動使用已安裝的 psycopg 3。"""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @field_validator("stocks", mode="before")
    @classmethod
    def parse_stocks(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        result: list[Stock] = []
        for raw in value.split(","):
            parts = [part.strip() for part in raw.split(":", 2)]
            if len(parts) != 3 or parts[0].upper() not in {"TW", "US"}:
                raise ValueError(f"無效的股票設定：{raw!r}，應為 MARKET:SYMBOL:NAME")
            result.append(Stock(parts[0].upper(), parts[1].upper(), parts[2]))
        return result
