import json
from decimal import Decimal
from app.db.supabase_client import get_client
from app.schemas.settings import SettingsResponse, SettingsUpdate

_DEFAULT_CATEGORIES = [
    "alimentacao", "transporte", "saude", "lazer", "compras",
    "salario", "investimento", "assinatura", "moradia", "pet",
    "mercado", "vestuario", "cosmeticos", "presentes", "miscelanea",
]

_DEFAULT_ESTABLISHMENTS: dict[str, list[str]] = {}


def _get(key: str) -> str | None:
    db = get_client()
    res = db.table("settings").select("value").eq("key", key).execute()
    if res.data:
        return res.data[0]["value"]
    return None


def _set(key: str, value: str) -> None:
    db = get_client()
    db.table("settings").upsert({"key": key, "value": value}, on_conflict="key").execute()


def get_settings() -> SettingsResponse:
    cats_raw = _get("active_categories")
    est_raw = _get("establishments")
    dm_raw = _get("detail_markets")
    ids_raw = _get("allowed_telegram_ids")
    return SettingsResponse(
        base_balance=Decimal(_get("base_balance") or "0"),
        scheduler_timezone=_get("scheduler_timezone") or "America/Sao_Paulo",
        active_categories=json.loads(cats_raw) if cats_raw else _DEFAULT_CATEGORIES,
        establishments=json.loads(est_raw) if est_raw else _DEFAULT_ESTABLISHMENTS,
        detail_markets=json.loads(dm_raw) if dm_raw else [],
        default_pix_card=_get("default_pix_card") or "",
        additional_system_prompt=_get("additional_system_prompt") or "",
        allowed_telegram_ids=json.loads(ids_raw) if ids_raw else [],
    )


def update_settings(data: SettingsUpdate) -> SettingsResponse:
    if data.base_balance is not None:
        _set("base_balance", str(data.base_balance))
    if data.scheduler_timezone is not None:
        _set("scheduler_timezone", data.scheduler_timezone)
    if data.active_categories is not None:
        _set("active_categories", json.dumps(data.active_categories, ensure_ascii=False))
    if data.establishments is not None:
        _set("establishments", json.dumps(data.establishments, ensure_ascii=False))
    if data.detail_markets is not None:
        _set("detail_markets", json.dumps(data.detail_markets, ensure_ascii=False))
    if data.default_pix_card is not None:
        _set("default_pix_card", data.default_pix_card)
    if data.additional_system_prompt is not None:
        _set("additional_system_prompt", data.additional_system_prompt)
    if data.allowed_telegram_ids is not None:
        _set("allowed_telegram_ids", json.dumps(data.allowed_telegram_ids))
    return get_settings()
