from decimal import Decimal
from app.db.supabase_client import get_client
from app.schemas.settings import SettingsResponse, SettingsUpdate


def _get(key: str) -> str | None:
    db = get_client()
    res = db.table("settings").select("value").eq("key", key).execute()
    if res.data:
        return res.data[0]["value"]
    return None


def _set(key: str, value: str) -> None:
    db = get_client()
    db.table("settings").upsert({"key": key, "value": value}).execute()


def get_settings() -> SettingsResponse:
    return SettingsResponse(
        base_balance=Decimal(_get("base_balance") or "0"),
        scheduler_timezone=_get("scheduler_timezone") or "America/Sao_Paulo",
    )


def update_settings(data: SettingsUpdate) -> SettingsResponse:
    if data.base_balance is not None:
        _set("base_balance", str(data.base_balance))
    if data.scheduler_timezone is not None:
        _set("scheduler_timezone", data.scheduler_timezone)
    return get_settings()
