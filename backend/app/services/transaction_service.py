from datetime import date
from uuid import UUID
from app.db.supabase_client import get_client
from app.schemas.transaction import TransactionCreate, TransactionUpdate, Transaction, TransactionList


_ALLOWED_SORT = {"date", "amount"}

def list_transactions(
    start: date | None = None,
    end: date | None = None,
    type_: str | None = None,
    category: str | None = None,
    card_id: UUID | None = None,
    user: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> TransactionList:
    db = get_client()
    q = db.table("transactions").select("*", count="exact")

    if start:
        q = q.gte("date", str(start))
    if end:
        q = q.lte("date", str(end))
    if type_:
        q = q.eq("type", type_)
    if category:
        q = q.eq("category", category)
    if card_id:
        q = q.eq("card_id", str(card_id))
    if user:
        q = q.eq("user", user)

    order_col = sort_by if sort_by in _ALLOWED_SORT else "date"
    desc = sort_dir != "asc"
    res = q.order(order_col, desc=desc).order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    items = [Transaction(**row) for row in res.data]
    return TransactionList(items=items, total=res.count or len(items))


def create_transaction(data: TransactionCreate) -> Transaction:
    db = get_client()
    payload = data.model_dump(mode="json")
    if payload.get("card_id"):
        payload["card_id"] = str(payload["card_id"])
    res = db.table("transactions").insert(payload).execute()
    return Transaction(**res.data[0])


def get_transaction(id: UUID) -> Transaction | None:
    db = get_client()
    res = db.table("transactions").select("*").eq("id", str(id)).execute()
    if not res.data:
        return None
    return Transaction(**res.data[0])


def update_transaction(id: UUID, data: TransactionUpdate) -> Transaction | None:
    db = get_client()
    payload = data.model_dump(exclude_none=True, mode="json")
    if "card_id" in payload and payload["card_id"]:
        payload["card_id"] = str(payload["card_id"])
    if not payload:
        return get_transaction(id)
    res = db.table("transactions").update(payload).eq("id", str(id)).execute()
    if not res.data:
        return None
    return Transaction(**res.data[0])


def delete_transaction(id: UUID) -> bool:
    db = get_client()
    res = db.table("transactions").delete().eq("id", str(id)).execute()
    return bool(res.data)


def get_period_totals(start: date, end: date) -> dict:
    db = get_client()
    res = (
        db.table("transactions")
        .select("type, amount, category")
        .gte("date", str(start))
        .lte("date", str(end))
        .execute()
    )
    income = sum(float(r["amount"]) for r in res.data if r["type"] == "income")
    expenses = sum(float(r["amount"]) for r in res.data if r["type"] == "expense")
    return {"income": income, "expenses": expenses, "rows": res.data}
