import calendar
from datetime import date
from app.services.transaction_service import get_period_totals
from app.schemas.analytics import AnalyticsResponse, AnalyticsSummary, MonthlyTrend


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def get_analytics(start: date, end: date) -> AnalyticsResponse:
    totals = get_period_totals(start, end)
    rows = totals["rows"]

    by_category: dict[str, float] = {}
    for r in rows:
        if r["type"] == "expense":
            by_category[r["category"]] = by_category.get(r["category"], 0) + float(r["amount"])

    top_category = max(by_category, key=by_category.get) if by_category else None

    summary = AnalyticsSummary(
        period=f"{start} to {end}",
        total_income=round(totals["income"], 2),
        total_expenses=round(totals["expenses"], 2),
        balance=round(totals["income"] - totals["expenses"], 2),
        by_category={k: round(v, 2) for k, v in by_category.items()},
        top_category=top_category,
    )

    trend: list[MonthlyTrend] = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        ms, me = _month_range(y, m)
        ms = max(ms, start)
        me = min(me, end)
        mt = get_period_totals(ms, me)
        trend.append(MonthlyTrend(
            month=f"{y}-{m:02d}",
            income=round(mt["income"], 2),
            expenses=round(mt["expenses"], 2),
            balance=round(mt["income"] - mt["expenses"], 2),
        ))
        m += 1
        if m > 12:
            m = 1
            y += 1

    return AnalyticsResponse(summary=summary, monthly_trend=trend)
