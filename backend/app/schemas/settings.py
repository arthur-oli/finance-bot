from decimal import Decimal
from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    base_balance: Decimal | None = None
    scheduler_timezone: str | None = None
    active_categories: list[str] | None = None
    establishments: dict[str, list[str]] | None = None
    detail_markets: list[str] | None = None
    default_pix_card: str | None = None
    additional_system_prompt: str | None = None
    allowed_telegram_ids: list[int] | None = None


class SettingsResponse(BaseModel):
    base_balance: Decimal
    scheduler_timezone: str
    active_categories: list[str]
    establishments: dict[str, list[str]]
    detail_markets: list[str]
    default_pix_card: str
    additional_system_prompt: str
    allowed_telegram_ids: list[int]
