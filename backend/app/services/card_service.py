from uuid import UUID
from app.db.supabase_client import get_client
from app.schemas.card import Card, CardCreate, CardUpdate


def list_cards(active_only: bool = True) -> list[Card]:
    db = get_client()
    q = db.table("cards").select("id,name,type,card_limit,closing_day,due_day,active,owner,created_at")
    if active_only:
        q = q.eq("active", True)
    res = q.order("name").execute()
    return [Card(**row) for row in res.data]


def create_card(data: CardCreate) -> Card:
    db = get_client()
    res = db.table("cards").insert(data.model_dump(exclude_none=True, mode="json")).execute()
    return Card(**res.data[0])


def get_card(id: UUID) -> Card | None:
    db = get_client()
    res = db.table("cards").select("id,name,type,card_limit,closing_day,due_day,active,owner,created_at").eq("id", str(id)).execute()
    if not res.data:
        return None
    return Card(**res.data[0])


def update_card(id: UUID, data: CardUpdate) -> Card | None:
    db = get_client()
    payload = data.model_dump(exclude_none=True, mode="json")
    if not payload:
        return get_card(id)
    res = db.table("cards").update(payload).eq("id", str(id)).execute()
    if not res.data:
        return None
    return Card(**res.data[0])


def delete_card(id: UUID) -> bool:
    db = get_client()
    res = db.table("cards").delete().eq("id", str(id)).execute()
    return bool(res.data)
