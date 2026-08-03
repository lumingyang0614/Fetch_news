from __future__ import annotations

import argparse
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import Settings
from app.database import make_session_factory
from app.fetcher import fetch_all
from app.universe import sync_universe


def main() -> None:
    parser = argparse.ArgumentParser(description="台股與美股公司新聞擷取器")
    parser.add_argument("command", choices=["run", "once", "sync-universe"], nargs="?", default="run")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    settings = Settings()
    sessions = make_session_factory(settings)
    job = lambda: fetch_all(settings, sessions)
    sync_job = lambda: sync_universe(settings, sessions)
    if args.command == "sync-universe":
        sync_job()
        return
    if args.command == "once":
        sync_job()
        job()
        return

    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    if settings.auto_sync_universe:
        sync_job()
        scheduler.add_job(
            sync_job,
            "cron",
            hour=settings.universe_sync_hour,
            id="sync-stock-universe",
            max_instances=1,
            coalesce=True,
        )
    scheduler.add_job(
        job,
        "interval",
        minutes=settings.fetch_interval_minutes,
        id="fetch-company-news",
        max_instances=1,
        coalesce=True,
        next_run_time=None if not settings.fetch_on_start else datetime.now(),
    )
    logging.info("排程器啟動，每 %d 分鐘執行一次", settings.fetch_interval_minutes)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
