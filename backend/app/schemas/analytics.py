from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    period: str
    total_income: float
    total_expenses: float
    balance: float
    by_category: dict[str, float]
    top_category: str | None


class MonthlyTrend(BaseModel):
    month: str
    income: float
    expenses: float
    balance: float


class AnalyticsResponse(BaseModel):
    summary: AnalyticsSummary
    monthly_trend: list[MonthlyTrend]
