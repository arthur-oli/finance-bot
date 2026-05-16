import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

_TZ = ZoneInfo("America/Sao_Paulo")
from app.services.transaction_service import get_period_totals
from app.services.subscription_service import monthly_subscriptions_total
from app.services.settings_service import get_settings
from app.schemas.forecast import ForecastResponse


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def _prev_months(year: int, month: int, n: int) -> list[tuple[int, int]]:
    result = []
    y, m = year, month
    for _ in range(n):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        result.append((y, m))
    return result


def get_forecast(target_year: int | None = None, target_month: int | None = None) -> ForecastResponse:
    today = datetime.now(_TZ).date()
    year = target_year or today.year
    month = target_month or today.month

    days_in_month = calendar.monthrange(year, month)[1]
    if year == today.year and month == today.month:
        days_elapsed = today.day
    else:
        days_elapsed = days_in_month

    # Historical data for last 3 months
    prev = _prev_months(year, month, 3)
    weights = [0.5, 0.3, 0.2]

    hist_income = []
    hist_expenses = []
    for (y, m) in prev:
        s, e = _month_range(y, m)
        totals = get_period_totals(s, e)
        hist_income.append(totals["income"])
        hist_expenses.append(totals["expenses"])

    avg_income = sum(w * v for w, v in zip(weights, hist_income))
    avg_expenses = sum(w * v for w, v in zip(weights, hist_expenses))

    # Current month actual
    cur_start, cur_end = _month_range(year, month)
    cur_totals = get_period_totals(cur_start, date(year, month, days_elapsed))
    pace = days_elapsed / days_in_month

    # Blended projection: 70% historical avg + 30% extrapolated current pace
    if pace > 0:
        paced_income = cur_totals["income"] / pace
        paced_expenses = cur_totals["expenses"] / pace
    else:
        paced_income = avg_income
        paced_expenses = avg_expenses

    projected_income = Decimal(str(round(0.7 * avg_income + 0.3 * paced_income, 2)))
    projected_expenses = Decimal(str(round(0.7 * avg_expenses + 0.3 * paced_expenses, 2)))

    subs_total = Decimal(str(round(monthly_subscriptions_total(), 2)))

    settings = get_settings()
    base = settings.base_balance

    projected_balance = base + projected_income - projected_expenses - subs_total

    return ForecastResponse(
        month=f"{year}-{month:02d}",
        projected_income=projected_income,
        projected_expenses=projected_expenses,
        projected_balance=projected_balance,
        subscriptions_total=subs_total,
        historical_avg_income=Decimal(str(round(avg_income, 2))),
        historical_avg_expenses=Decimal(str(round(avg_expenses, 2))),
        pace_factor=Decimal(str(round(pace, 4))),
        days_elapsed=days_elapsed,
        days_in_month=days_in_month,
    )
