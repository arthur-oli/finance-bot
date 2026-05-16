from decimal import Decimal
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    base_balance: Decimal | None = None
    scheduler_timezone: str | None = None


class SettingsResponse(BaseModel):
    base_balance: Decimal
    scheduler_timezone: str
