from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.deps.auth import verify_api_key
from app.schemas.transaction import Transaction, TransactionCreate, TransactionList, TransactionUpdate
import app.services.transaction_service as svc

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=TransactionList)
def list_transactions(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    type: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    card_id: Optional[UUID] = Query(None),
    user: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None),
    sort_dir: str = Query("desc"),
):
    return svc.list_transactions(start, end, type, category, card_id, user, limit, offset, sort_by, sort_dir)


@router.post("/", response_model=Transaction, status_code=201)
def create_transaction(body: TransactionCreate):
    return svc.create_transaction(body)


@router.get("/{id}", response_model=Transaction)
def get_transaction(id: UUID):
    tx = svc.get_transaction(id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.patch("/{id}", response_model=Transaction)
def update_transaction(id: UUID, body: TransactionUpdate):
    tx = svc.update_transaction(id, body)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.delete("/{id}", status_code=204)
def delete_transaction(id: UUID):
    if not svc.delete_transaction(id):
        raise HTTPException(404, "Transaction not found")
