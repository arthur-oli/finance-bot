from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class CardCreate(BaseModel):
    name: str
    type: Literal["credit", "debit"]
    card_limit: Optional[Decimal] = Field(default=None, gt=0)
    closing_day: Optional[int] = Field(default=None, ge=1, le=31)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    owner: Optional[str] = None


class CardUpdate(BaseModel):
    name: Optional[str] = None
    card_limit: Optional[Decimal] = Field(default=None, gt=0)
    closing_day: Optional[int] = Field(default=None, ge=1, le=31)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    active: Optional[bool] = None
    owner: Optional[str] = None


class Card(BaseModel):
    id: UUID
    name: str
    type: str
    card_limit: Optional[Decimal] = None
    closing_day: Optional[int] = None
    due_day: Optional[int] = None
    active: bool
    is_default_debit: bool = False
    is_default_credit: bool = False
    owner: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
