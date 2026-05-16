from decimal import Decimal
from pydantic import BaseModel


class ForecastResponse(BaseModel):
    month: str
    projected_income: Decimal
    projected_expenses: Decimal
    projected_balance: Decimal
    subscriptions_total: Decimal
    historical_avg_income: Decimal
    historical_avg_expenses: Decimal
    pace_factor: Decimal
    days_elapsed: int
    days_in_month: int
