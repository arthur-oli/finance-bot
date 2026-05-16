from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    name: str
    target_amount: Decimal = Field(gt=0, decimal_places=2)
    current_amount: Decimal = Field(default=Decimal("0"), ge=0)
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = Field(default=None, gt=0)
    current_amount: Optional[Decimal] = Field(default=None, ge=0)
    deadline: Optional[date] = None
    completed: Optional[bool] = None


class Goal(BaseModel):
    id: UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: Optional[date] = None
    completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}
