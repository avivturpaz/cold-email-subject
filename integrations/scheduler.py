"""Background jobs wrapper around APScheduler."""

from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = BackgroundScheduler()


def add_interval_job(func, minutes: int, job_id: str) -> None:
    _scheduler.add_job(func, "interval", minutes=minutes, id=job_id, replace_existing=True)


def add_daily_job(func, hour: int, minute: int, job_id: str) -> None:
    _scheduler.add_job(func, "cron", hour=hour, minute=minute, id=job_id, replace_existing=True)


def start() -> None:
    if not _scheduler.running:
        _scheduler.start()


def stop() -> None:
    if _scheduler.running:
        _scheduler.shutdown()
