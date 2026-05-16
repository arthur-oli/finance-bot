import base64
import io
import os
import json
from datetime import date

import httpx
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.environ["GROQ_API_KEY"]
_BASE = "https://api.groq.com/openai/v1/chat/completions"
_MODEL_TEXT = "llama-3.3-70b-versatile"
_MODEL_VISION = "meta-llama/llama-4-scout-17b-16e-instruct"

_SYSTEM_TPL = """Assistente financeiro pessoal. Extraia uma transação da mensagem e retorne APENAS JSON válido:
{{"type":"income|expense","amount":0.0,"category":"alimentacao|transporte|saude|lazer|compras|salario|investimento|assinatura|moradia|pet|mercado|vestuario|cosmeticos|presentes|miscelanea","description":"texto curto","date":"YYYY-MM-DD","card":null}}
"card" = nome exato do cartão quando mencionado, ou null. Palavras "pix", "débito", "conta" sem outro cartão → "Nubank Conta".
Se não identificar transação: {{"error":"motivo"}}

Estabelecimentos conhecidos:
alimentacao: Expresso Move, Market4U, Guiju, Hati Pastel, Mafalda Bistro, Sodexo, iFood/Ifd*, Portão Point
mercado: Dalpar, Condor (supermercados — compras mistas de alimentação e não-alimentares)
transporte: Uber, 99
assinatura: Spotify, Claude.ai, Amazon Prime, TIM Pós, iFood Club
moradia: condomínio, COPEL, energia elétrica, aluguel, água, gás, SANEPAR, luz, internet débito automático
saude: Pague Menos
pet: Petlove, Petlove Saúde, Rei dos Animais, Flexipet, pet shop, ração, veterinário
lazer: Factory Games, hotel

Cartões: {cards}"""

_RECEIPT_TPL = """Especialista em OCR de comprovantes financeiros.

Para comprovantes de supermercado/mercado (Dalpar, Condor, Carrefour, Extra, Atacadão, etc.), leia cada item listado e retorne um ARRAY JSON separando os valores por categoria:
- "alimentacao": alimentos, bebidas, hortifrúti, laticínios, carnes, padaria, congelados, temperos, snacks
- "mercado": limpeza, higiene pessoal, utilidades domésticas, pet food, outros não-alimentares
- "cosmeticos": cosméticos, perfumaria, maquiagem, cuidados com a pele/cabelo
- "vestuario": roupas, calçados, acessórios de moda
Inclua somente as categorias que tiverem itens. Os valores devem somar ao total do comprovante.

Para outros estabelecimentos, retorne um único objeto JSON.

Formato de cada objeto:
{{"type":"income|expense","amount":0.0,"category":"alimentacao|transporte|saude|lazer|compras|salario|investimento|assinatura|moradia|pet|mercado|vestuario|cosmeticos|presentes|miscelanea","description":"estabelecimento — categoria","date":"YYYY-MM-DD","card":null}}

"card" = nome exato do cartão se identificável no comprovante, ou null.
Se não conseguir ler: {{"error":"motivo"}}

Cartões: {cards}"""


def _cards_str(cards: list[dict]) -> str:
    return ", ".join(c["name"] for c in cards) if cards else "nenhum"


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


def interpret_text(text: str, cards: list[dict] | None = None) -> dict:
    cards = cards or []
    system = _SYSTEM_TPL.format(cards=_cards_str(cards))
    today = str(date.today())
    result = _call(_MODEL_TEXT, system, [{"role": "user", "content": f"Data de hoje: {today}\n\n{text}"}])
    if "card" in result:
        result["card_id"] = _resolve_card(result.pop("card"), cards)
    return result


def interpret_image(image_bytes: bytes, cards: list[dict] | None = None, caption: str = "", mime_type: str = "image/jpeg") -> dict | list:
    cards = cards or []
    system = _RECEIPT_TPL.format(cards=_cards_str(cards))
    today = str(date.today())
    img = Image.open(io.BytesIO(image_bytes))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    hint = f" Legenda do usuário: '{caption}'." if caption else ""
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
