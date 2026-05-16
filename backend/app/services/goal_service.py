from uuid import UUID
from app.db.supabase_client import get_client
from app.schemas.goal import Goal, GoalCreate, GoalUpdate


def list_goals(include_completed: bool = False) -> list[Goal]:
    db = get_client()
    q = db.table("goals").select("*")
    if not include_completed:
        q = q.eq("completed", False)
    res = q.order("created_at", desc=True).execute()
    return [Goal(**row) for row in res.data]


def create_goal(data: GoalCreate) -> Goal:
    db = get_client()
    res = db.table("goals").insert(data.model_dump(mode="json")).execute()
    return Goal(**res.data[0])


def get_goal(id: UUID) -> Goal | None:
    db = get_client()
    res = db.table("goals").select("*").eq("id", str(id)).execute()
    if not res.data:
        return None
    return Goal(**res.data[0])


def update_goal(id: UUID, data: GoalUpdate) -> Goal | None:
    db = get_client()
    payload = data.model_dump(exclude_none=True, mode="json")
    if not payload:
        return get_goal(id)
    res = db.table("goals").update(payload).eq("id", str(id)).execute()
    if not res.data:
        return None
    return Goal(**res.data[0])


def delete_goal(id: UUID) -> bool:
    db = get_client()
    res = db.table("goals").delete().eq("id", str(id)).execute()
    return bool(res.data)
