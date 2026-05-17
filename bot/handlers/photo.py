import os
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import structlog
from bot.services import backend_client as bc
from bot.services.ai import interpret_image, validate_transaction

_raw = os.environ.get("TELEGRAM_USER_IDS", os.environ.get("TELEGRAM_USER_ID", ""))
_ALLOWED = {int(x.strip()) for x in _raw.split(",") if x.strip()}

log = structlog.get_logger()

PENDING_KEY = "pending_photo_tx"


def _fmt_brl(v) -> str:
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _cards_for_sender(cards: list[dict], first_name: str, text: str = "") -> list[dict]:
    owners = {c["owner"] for c in cards if c.get("owner")}
    name_lower = first_name.lower()
    # If text explicitly mentions another user's owner name → show all cards
    for owner in owners:
        if owner.lower() != name_lower and owner.lower() in text.lower():
            return cards
    # Return cards owned by this user or shared (no owner set)
    return [c for c in cards if not c.get("owner") or c["owner"].lower() == name_lower]


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📷 Processando comprovante...")

    photo = update.message.photo[-1]
    file = await ctx.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    caption = update.message.caption or ""

    try:
        all_cards = bc.list_cards()
        cards = _cards_for_sender(all_cards, update.effective_user.first_name, caption)
        parsed = interpret_image(bytes(image_bytes), cards, caption=caption)
    except Exception as e:
        log.error("interpret_image.error", error=str(e))
        await update.message.reply_text("Erro ao processar imagem. Tente novamente.")
        return

    if isinstance(parsed, dict) and "error" in parsed:
        await update.message.reply_text(
            f"Não consegui ler o comprovante: {parsed['error']}\n\n"
            "Tente enviar uma foto mais nítida."
        )
        return

    # Normalize to list for uniform handling
    items = parsed if isinstance(parsed, list) else [parsed]

    # Validate each item from LLM
    validated_items = []
    for item in items:
        try:
            validated_items.append(validate_transaction(item))
        except ValueError as e:
            log.warning("validate_transaction.rejected", reason=str(e))
            await update.message.reply_text("Não consegui validar os dados do comprovante. Tente novamente.")
            return

    sender = update.effective_user.first_name
    for item in validated_items:
        item["user"] = sender
    ctx.user_data[PENDING_KEY] = validated_items

    tx_date = validated_items[0].get("date", str(date.today()))
    card_id = validated_items[0].get("card_id")
    card_name = ""
    if card_id:
        card = next((c for c in cards if c["id"] == card_id), None)
        card_name = f"\n💳 Cartão: {card['name']}" if card else ""

    if len(validated_items) == 1:
        t = validated_items[0]
        icon = "✅" if t["type"] == "income" else "❌"
        text_msg = (
            f"{icon} *Comprovante lido:*\n\n"
            f"📅 Data: {tx_date}\n"
            f"📝 Descrição: {t.get('description', '-')}\n"
            f"🏷️ Categoria: {t.get('category', '-')}\n"
            f"💰 Valor: {_fmt_brl(t.get('amount', 0))}"
            f"{card_name}\n\n"
            "Confirmar registro?"
        )
    else:
        total = sum(float(t.get("amount", 0)) for t in validated_items)
        lines = [f"📷 *Comprovante lido ({len(validated_items)} categorias):*\n", f"📅 Data: {tx_date}\n"]
        for t in validated_items:
            icon = "✅" if t["type"] == "income" else "❌"
            lines.append(f"{icon} {t.get('category', '-').capitalize()}: {_fmt_brl(t.get('amount', 0))}")
        lines.append(f"\n💰 Total: {_fmt_brl(total)}{card_name}\n\nConfirmar registro?")
        text_msg = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data="photo_confirm"),
        InlineKeyboardButton("❌ Cancelar", callback_data="photo_cancel"),
    ]])
    await update.message.reply_text(text_msg, reply_markup=keyboard, parse_mode="Markdown")


async def handle_photo_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in _ALLOWED:
        return

    if query.data == "photo_cancel":
        ctx.user_data.pop(PENDING_KEY, None)
        await query.edit_message_text("❌ Comprovante descartado.")
        return

    if query.data == "photo_confirm":
        pending = ctx.user_data.pop(PENDING_KEY, None)
        if not pending:
            await query.edit_message_text("Nenhum comprovante pendente.")
            return
        try:
            for t in pending:
                tx_date = date.fromisoformat(t.get("date", str(date.today())))
                bc.create_transaction(
                    date_=tx_date,
                    type_=t["type"],
                    category=t["category"],
                    description=t["description"],
                    amount=float(t["amount"]),
                    card_id=t.get("card_id"),
                    user=t.get("user"),
                )
            if len(pending) == 1:
                t = pending[0]
                await query.edit_message_text(
                    f"✅ Comprovante registrado!\n"
                    f"{t['description']} — {_fmt_brl(t['amount'])}"
                )
            else:
                total = sum(float(t["amount"]) for t in pending)
                lines = [f"✅ {len(pending)} transações registradas!"]
                for t in pending:
                    lines.append(f"• {t['category'].capitalize()}: {_fmt_brl(t['amount'])}")
                lines.append(f"Total: {_fmt_brl(total)}")
                await query.edit_message_text("\n".join(lines))
        except Exception as e:
            log.error("photo_confirm.error", error=str(e))
            await query.edit_message_text("Erro ao salvar. Tente novamente.")
