import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    date: datetime.date
    type: Literal["income", "expense"]
    category: str
    description: str
    amount: float = Field(gt=0)
    card_id: Optional[UUID] = None
    user: Optional[str] = None


class TransactionUpdate(BaseModel):
    date: Optional[datetime.date] = None
    type: Optional[Literal["income", "expense"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    card_id: Optional[UUID] = None
    user: Optional[str] = None


class Transaction(BaseModel):
    id: UUID
    date: datetime.date
    type: str
    category: str
    description: str
    amount: float
    card_id: Optional[UUID] = None
    user: Optional[str] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class TransactionList(BaseModel):
    items: list[Transaction]
    total: int
