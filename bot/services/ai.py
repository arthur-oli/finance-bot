import base64
import io
import os
import json
import time
from datetime import date, timedelta

import httpx
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.environ["GROQ_API_KEY"]
_BASE = "https://api.groq.com/openai/v1/chat/completions"
_MODEL_TEXT = "llama-3.3-70b-versatile"
_MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_TEXT_LEN = 500

# ── Config cache ──────────────────────────────────────────────────────────────
_CONFIG_CACHE: dict | None = None
_CONFIG_TS: float = 0
_CONFIG_TTL = 300  # 5 minutes

_DEFAULT_CATEGORIES = [
    "alimentacao", "transporte", "saude", "lazer", "compras",
    "salario", "investimento", "assinatura", "moradia", "pet",
    "mercado", "vestuario", "cosmeticos", "presentes", "miscelanea",
]

_DEFAULT_ESTABLISHMENTS: dict[str, list[str]] = {}


def _get_config() -> dict:
    global _CONFIG_CACHE, _CONFIG_TS
    now = time.time()
    if _CONFIG_CACHE is None or now - _CONFIG_TS > _CONFIG_TTL:
        try:
            from bot.services.backend_client import get_bot_config
            _CONFIG_CACHE = get_bot_config()
            _CONFIG_TS = now
        except Exception:
            if _CONFIG_CACHE is None:
                _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def _active_categories() -> list[str]:
    return _get_config().get("active_categories") or _DEFAULT_CATEGORIES


def _valid_categories() -> frozenset[str]:
    return frozenset(_active_categories())


def _cards_str(cards: list[dict]) -> str:
    return ", ".join(c["name"] for c in cards) if cards else "nenhum"


def _build_system_prompt(cards: list[dict]) -> str:
    cfg = _get_config()
    cats = _active_categories()
    cat_str = "|".join(cats)
    establishments: dict[str, list[str]] = cfg.get("establishments") or _DEFAULT_ESTABLISHMENTS
    pix_card: str = cfg.get("default_pix_card") or ""
    extra: str = cfg.get("additional_system_prompt") or ""

    est_lines = [
        f"{cat}: {', '.join(places)}"
        for cat, places in establishments.items()
        if places and cat in cats
    ]
    est_section = "\n".join(est_lines) if est_lines else ""

    pix_line = f' Palavras "pix", "débito", "conta" sem outro cartão → "{pix_card}".' if pix_card else ""
    prompt = (
        f'Assistente financeiro pessoal. Extraia uma transação da mensagem e retorne APENAS JSON válido:\n'
        f'{{"type":"income|expense","amount":0.0,"category":"{cat_str}","description":"texto curto","date":"YYYY-MM-DD","card":null}}\n'
        f'"card" = nome exato do cartão quando mencionado, ou null.{pix_line}\n'
        f'Se não identificar transação: {{"error":"motivo"}}'
    )
    if est_section:
        prompt += f"\n\nEstabelecimentos conhecidos:\n{est_section}"
    prompt += f"\n\nCartões: {_cards_str(cards)}"
    if extra:
        prompt += f"\n\n{extra}"
    return prompt


def _build_receipt_prompt(cards: list[dict]) -> str:
    cfg = _get_config()
    cats = _active_categories()
    cat_str = "|".join(cats)
    detail_markets: list[str] = cfg.get("detail_markets") or []
    extra: str = cfg.get("additional_system_prompt") or ""

    markets_str = ", ".join(detail_markets) if detail_markets else "supermercados"

    prompt = (
        f"Especialista em OCR de comprovantes financeiros.\n\n"
        f"Para comprovantes de supermercado/mercado ({markets_str}, Carrefour, Extra, Atacadão, etc.), "
        f"leia cada item listado e retorne um ARRAY JSON separando os valores por categoria:\n"
        f'- "alimentacao": alimentos, bebidas, hortifrúti, laticínios, carnes, padaria, congelados, temperos, snacks\n'
        f'- "mercado": limpeza, higiene pessoal, utilidades domésticas, pet food, outros não-alimentares\n'
        f'- "cosmeticos": cosméticos, perfumaria, maquiagem, cuidados com a pele/cabelo\n'
        f'- "vestuario": roupas, calçados, acessórios de moda\n'
        f"Inclua somente as categorias que tiverem itens. Os valores devem somar ao total do comprovante.\n\n"
        f"Para outros estabelecimentos, retorne um único objeto JSON.\n\n"
        f"Formato de cada objeto:\n"
        f'{{"type":"income|expense","amount":0.0,"category":"{cat_str}","description":"estabelecimento — categoria","date":"YYYY-MM-DD","card":null}}\n\n'
        f'"card" = nome exato do cartão se identificável no comprovante, ou null.\n'
        f'Se não conseguir ler: {{"error":"motivo"}}\n\n'
        f"Cartões: {_cards_str(cards)}"
    )
    if extra:
        prompt += f"\n\n{extra}"
    return prompt


def _resolve_card(card_name: str | None, cards: list[dict]) -> str | None:
    if not card_name:
        return None
    name_lower = card_name.lower()
    for c in cards:
        if c["name"].lower() in name_lower or name_lower in c["name"].lower():
            return c["id"]
    return None


def _parse(text: str) -> dict:
    raw = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"error": "Não consegui interpretar a resposta."}


def _call(model: str, system: str, messages: list) -> dict:
    r = httpx.post(
        _BASE,
        headers={"Authorization": f"Bearer {_API_KEY}"},
        json={"model": model, "messages": [{"role": "system", "content": system}] + messages},
        timeout=30,
    )
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def validate_transaction(data: dict) -> dict:
    """Validate and sanitize a transaction dict from LLM output."""
    errors: list[str] = []

    if data.get("type") not in ("income", "expense"):
        errors.append(f"tipo inválido: {data.get('type')!r}")

    try:
        amount = float(data["amount"])
        if amount <= 0:
            errors.append("valor deve ser positivo")
        elif amount > 50_000:
            errors.append(f"valor acima do limite: R$ {amount:,.2f}")
        else:
            data["amount"] = round(amount, 2)
    except (KeyError, TypeError, ValueError):
        errors.append("valor não é um número válido")

    cat = data.get("category", "")
    if cat not in _valid_categories():
        errors.append(f"categoria inválida: {cat!r}")

    desc = str(data.get("description", "")).strip()
    if not desc:
        errors.append("descrição vazia")
    else:
        data["description"] = desc[:200]

    date_str = data.get("date", "")
    try:
        tx_date = date.fromisoformat(str(date_str))
        today = date.today()
        if tx_date > today:
            data["date"] = str(today)
        elif tx_date < today - timedelta(days=730):
            errors.append(f"data muito antiga: {date_str}")
    except (ValueError, TypeError):
        data["date"] = str(date.today())

    if errors:
        raise ValueError("Dados inválidos retornados pelo LLM: " + "; ".join(errors))

    return data


def interpret_text(text: str, cards: list[dict] | None = None) -> dict:
    cards = cards or []
    system = _build_system_prompt(cards)
    today = str(date.today())
    safe_text = text[:MAX_TEXT_LEN]
    result = _call(_MODEL_TEXT, system, [{"role": "user", "content": f"Data de hoje: {today}\n\n{safe_text}"}])
    if "card" in result:
        result["card_id"] = _resolve_card(result.pop("card"), cards)
    return result


def interpret_image(image_bytes: bytes, cards: list[dict] | None = None, caption: str = "", mime_type: str = "image/jpeg") -> dict | list:
    cards = cards or []
    system = _build_receipt_prompt(cards)
    today = str(date.today())
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    safe_caption = caption[:MAX_TEXT_LEN]
    hint = f" Legenda do usuário: '{safe_caption}'." if safe_caption else ""
    result = _call(_MODEL_VISION, system, [{"role": "user", "content": [
        {"type": "text", "text": f"Data de hoje: {today}.{hint} Extraia os dados desta transação."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
    ]}])
    if isinstance(result, list):
        for item in result:
            if "card" in item:
                item["card_id"] = _resolve_card(item.pop("card"), cards)
        return result
    if "card" in result:
        result["card_id"] = _resolve_card(result.pop("card"), cards)
    return result
