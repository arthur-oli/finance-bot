import os
import time
from decimal import Decimal
from datetime import date
import httpx
from dotenv import load_dotenv

load_dotenv()

_BASE = os.environ.get("BACKEND_URL", "http://localhost:8000")
_KEY = os.environ.get("API_SECRET_KEY", "")
_HEADERS = {"X-API-Key": _KEY, "Content-Type": "application/json"}
_TIMEOUT = 15.0


def _client() -> httpx.Client:
    return httpx.Client(base_url=_BASE, headers=_HEADERS, timeout=_TIMEOUT)


def create_transaction(
    date_: date,
    type_: str,
    category: str,
    description: str,
    amount: float,
    card_id: str | None = None,
    user: str | None = None,
) -> dict:
    payload: dict = {
        "date": str(date_),
        "type": type_,
        "category": category,
        "description": description,
        "amount": str(round(amount, 2)),
    }
    if card_id:
        payload["card_id"] = card_id
    if user:
        payload["user"] = user
    with _client() as c:
        res = c.post("/api/transactions/", json=payload)
        res.raise_for_status()
        return res.json()


def get_balance_summary() -> dict:
    today = date.today()
    start = date(today.year, today.month, 1)
    with _client() as c:
        res = c.get("/api/analytics/", params={"start": str(start), "end": str(today)})
        res.raise_for_status()
        return res.json()


def get_forecast() -> dict:
    with _client() as c:
        res = c.get("/api/forecast/")
        res.raise_for_status()
        return res.json()


def list_subscriptions() -> list[dict]:
    with _client() as c:
        res = c.get("/api/subscriptions/")
        res.raise_for_status()
        return res.json()


def list_goals() -> list[dict]:
    with _client() as c:
        res = c.get("/api/goals/")
        res.raise_for_status()
        return res.json()


def list_cards() -> list[dict]:
    with _client() as c:
        res = c.get("/api/cards/")
        res.raise_for_status()
        return res.json()


def get_bot_config() -> dict:
    with _client() as c:
        res = c.get("/api/settings/")
        res.raise_for_status()
        return res.json()


_allowed_cache: tuple[frozenset[int], float] = (frozenset(), 0.0)
_ALLOWED_TTL = 300


def get_allowed_ids() -> frozenset[int]:
    global _allowed_cache
    ids, ts = _allowed_cache
    if ids and time.time() - ts < _ALLOWED_TTL:
        return ids
    try:
        config = get_bot_config()
        id_list = config.get("allowed_telegram_ids") or []
        if id_list:
            new_ids = frozenset(int(x) for x in id_list)
        else:
            raw = os.environ.get("TELEGRAM_USER_IDS", os.environ.get("TELEGRAM_USER_ID", ""))
            new_ids = frozenset(int(x.strip()) for x in raw.split(",") if x.strip())
    except Exception:
        if ids:
            return ids
        raw = os.environ.get("TELEGRAM_USER_IDS", os.environ.get("TELEGRAM_USER_ID", ""))
        new_ids = frozenset(int(x.strip()) for x in raw.split(",") if x.strip())
    _allowed_cache = (new_ids, time.time())
    return new_ids


def list_transactions(start: date | None = None, end: date | None = None, limit: int = 10) -> dict:
    params: dict = {"limit": limit}
    if start:
        params["start"] = str(start)
    if end:
        params["end"] = str(end)
    with _client() as c:
        res = c.get("/api/transactions/", params=params)
        res.raise_for_status()
        return res.json()
