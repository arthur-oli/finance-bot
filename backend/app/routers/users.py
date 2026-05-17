from fastapi import APIRouter, Depends
from app.deps.auth import verify_api_key
from app.db.supabase_client import get_client

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("/")
def list_users() -> list[str]:
    db = get_client()
    res = db.table("transactions").select("user_name").execute()
    return sorted({r["user_name"] for r in res.data if r.get("user_name")})
