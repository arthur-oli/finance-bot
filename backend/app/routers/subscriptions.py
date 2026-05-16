from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.deps.auth import verify_api_key
from app.schemas.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate
import app.services.subscription_service as svc

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/", response_model=list[Subscription])
def list_subscriptions(active_only: bool = Query(True)):
    return svc.list_subscriptions(active_only)


@router.post("/", response_model=Subscription, status_code=201)
def create_subscription(body: SubscriptionCreate):
    return svc.create_subscription(body)


@router.patch("/{id}", response_model=Subscription)
def update_subscription(id: UUID, body: SubscriptionUpdate):
    sub = svc.update_subscription(id, body)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    return sub


@router.delete("/{id}", status_code=204)
def delete_subscription(id: UUID):
    if not svc.delete_subscription(id):
        raise HTTPException(404, "Subscription not found")
