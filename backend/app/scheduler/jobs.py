import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

log = structlog.get_logger()
_scheduler: AsyncIOScheduler | None = None


async def _daily_summary():
    log.info("scheduler.daily_summary", msg="running daily summary job")
    # Placeholder: send daily summary via Telegram or log it
    from datetime import date
    from app.services.transaction_service import get_period_totals
    today = date.today()
    start = date(today.year, today.month, 1)
    totals = get_period_totals(start, today)
    log.info(
        "scheduler.daily_summary.result",
        month_income=totals["income"],
        month_expenses=totals["expenses"],
    )


async def _update_subscriptions_next_date():
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from app.db.supabase_client import get_client
    db = get_client()
    today = date.today()
    res = db.table("subscriptions").select("*").eq("active", True).execute()
    for sub in res.data:
        next_dt = date.fromisoformat(sub["next_date"])
        if next_dt <= today:
            if sub["frequency"] == "monthly":
                new_next = next_dt + relativedelta(months=1)
            else:
                new_next = next_dt + relativedelta(years=1)
            db.table("subscriptions").update({"next_date": str(new_next)}).eq("id", sub["id"]).execute()
            log.info("scheduler.subscription_updated", name=sub["name"], new_next=str(new_next))


def start_scheduler():
    global _scheduler
    tz = os.getenv("SCHEDULER_TIMEZONE", "America/Sao_Paulo")
    _scheduler = AsyncIOScheduler(timezone=tz)
    _scheduler.add_job(_daily_summary, CronTrigger(hour=8, minute=0, timezone=tz))
    _scheduler.add_job(_update_subscriptions_next_date, CronTrigger(hour=0, minute=5, timezone=tz))
    _scheduler.start()
    log.info("scheduler.started", timezone=tz)
