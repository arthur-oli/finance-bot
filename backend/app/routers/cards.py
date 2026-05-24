from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.deps.auth import verify_api_key
from app.schemas.card import Card, CardCreate, CardUpdate
import app.services.card_service as svc

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[Card])
def list_cards(active_only: bool = Query(True)):
    return svc.list_cards(active_only)


@router.post("/", response_model=Card, status_code=201)
def create_card(body: CardCreate):
    return svc.create_card(body)


# Rotas literais DEVEM vir antes de /{id} pra nao virar UUID
@router.delete("/default/debit", status_code=204)
def clear_default_debit():
    svc.clear_default_debit()


@router.delete("/default/credit", status_code=204)
def clear_default_credit():
    svc.clear_default_credit()


@router.post("/{id}/default/debit", response_model=Card)
def set_default_debit(id: UUID):
    card = svc.set_default_debit(id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.post("/{id}/default/credit", response_model=Card)
def set_default_credit(id: UUID):
    card = svc.set_default_credit(id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.get("/{id}", response_model=Card)
def get_card(id: UUID):
    card = svc.get_card(id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.patch("/{id}", response_model=Card)
def update_card(id: UUID, body: CardUpdate):
    card = svc.update_card(id, body)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.delete("/{id}", status_code=204)
def delete_card(id: UUID):
    if not svc.delete_card(id):
        raise HTTPException(404, "Card not found")
