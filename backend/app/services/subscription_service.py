from uuid import UUID
from app.db.supabase_client import get_client
from app.schemas.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate


def list_subscriptions(active_only: bool = True) -> list[Subscription]:
    db = get_client()
    q = db.table("subscriptions").select("*")
    if active_only:
        q = q.eq("active", True)
    res = q.order("name").execute()
    return [Subscription(**row) for row in res.data]


def create_subscription(data: SubscriptionCreate) -> Subscription:
    db = get_client()
    res = db.table("subscriptions").insert(data.model_dump(mode="json")).execute()
    return Subscription(**res.data[0])


def update_subscription(id: UUID, data: SubscriptionUpdate) -> Subscription | None:
    db = get_client()
    payload = data.model_dump(exclude_none=True, mode="json")
    if not payload:
        return get_subscription(id)
    res = db.table("subscriptions").update(payload).eq("id", str(id)).execute()
    if not res.data:
        return None
    return Subscription(**res.data[0])


def get_subscription(id: UUID) -> Subscription | None:
    db = get_client()
    res = db.table("subscriptions").select("*").eq("id", str(id)).execute()
    if not res.data:
        return None
    return Subscription(**res.data[0])


def delete_subscription(id: UUID) -> bool:
    db = get_client()
    res = db.table("subscriptions").update({"active": False}).eq("id", str(id)).execute()
    return bool(res.data)


def monthly_subscriptions_total() -> float:
    subs = list_subscriptions()
    total = 0.0
    for s in subs:
        if s.frequency == "monthly":
            total += float(s.amount)
        elif s.frequency == "annual":
            total += float(s.amount) / 12
    return total
