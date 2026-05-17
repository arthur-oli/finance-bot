import time
from fastapi import APIRouter, Depends
from app.deps.auth import verify_api_key
from app.db.supabase_client import get_client

router = APIRouter(dependencies=[Depends(verify_api_key)])

_cache: tuple[list[str], float] = ([], 0.0)
_TTL = 300


@router.get("/")
def list_users() -> list[str]:
    global _cache
    users, ts = _cache
    if users and time.time() - ts < _TTL:
        return users
    db = get_client()
    res = db.table("transactions").select("user").not_.is_("user", "null").execute()
    result = sorted({r["user"] for r in res.data if r.get("user")})
    _cache = (result, time.time())
    return result
