from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class SubscriptionCreate(BaseModel):
    name: str
    amount: Decimal = Field(gt=0, decimal_places=2)
    frequency: Literal["monthly", "annual"]
    next_date: date


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=0)
    frequency: Optional[Literal["monthly", "annual"]] = None
    next_date: Optional[date] = None
    active: Optional[bool] = None


class Subscription(BaseModel):
    id: UUID
    name: str
    amount: Decimal
    frequency: str
    next_date: date
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
