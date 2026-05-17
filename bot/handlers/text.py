import os
from datetime import date
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import structlog
from bot.services import backend_client as bc
from bot.services.ai import interpret_text, validate_transaction


log = structlog.get_logger()

PENDING_KEY = "pending_tx"


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


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return

    await update.message.reply_text("🤔 Analisando...")

    try:
        all_cards = bc.list_cards()
        cards = _cards_for_sender(all_cards, update.effective_user.first_name, text)
        parsed = interpret_text(text, cards)
    except Exception as e:
        log.error("interpret_text.error", error=str(e))
        await update.message.reply_text("Erro ao processar mensagem. Tente novamente.")
        return

    if "error" in parsed:
        await update.message.reply_text(
            f"Não entendi: {parsed['error']}\n\n"
            "Tente algo como: _gastei 50 no mercado_ ou _recebi 3000 de salário_",
            parse_mode="Markdown",
        )
        return

    try:
        parsed = validate_transaction(parsed)
    except ValueError as e:
        log.warning("validate_transaction.rejected", reason=str(e))
        await update.message.reply_text("Não consegui validar os dados da transação. Tente reformular.")
        return

    parsed["user"] = update.effective_user.first_name
    ctx.user_data[PENDING_KEY] = parsed

    card_name = ""
    if parsed.get("card_id"):
        card = next((c for c in cards if c["id"] == parsed["card_id"]), None)
        card_name = f"\n💳 Cartão: {card['name']}" if card else ""

    icon = "✅" if parsed["type"] == "income" else "❌"
    tx_date = parsed.get("date", str(date.today()))
    text_msg = (
        f"{icon} *Transação identificada:*\n\n"
        f"📅 Data: {tx_date}\n"
        f"📝 Descrição: {parsed.get('description', '-')}\n"
        f"🏷️ Categoria: {parsed.get('category', '-')}\n"
        f"💰 Valor: {_fmt_brl(parsed.get('amount', 0))}\n"
        f"Tipo: {'Receita' if parsed['type'] == 'income' else 'Despesa'}"
        f"{card_name}\n\n"
        "Confirmar?"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data="tx_confirm"),
        InlineKeyboardButton("❌ Cancelar", callback_data="tx_cancel"),
    ]])
    await update.message.reply_text(text_msg, reply_markup=keyboard, parse_mode="Markdown")


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id not in bc.get_allowed_ids():
        return

    if query.data == "tx_cancel":
        ctx.user_data.pop(PENDING_KEY, None)
        await query.edit_message_text("❌ Transação cancelada.")
        return

    if query.data == "tx_confirm":
        pending = ctx.user_data.pop(PENDING_KEY, None)
        if not pending:
            await query.edit_message_text("Nenhuma transação pendente.")
            return
        try:
            tx_date = date.fromisoformat(pending.get("date", str(date.today())))
            bc.create_transaction(
                date_=tx_date,
                type_=pending["type"],
                category=pending["category"],
                description=pending["description"],
                amount=float(pending["amount"]),
                card_id=pending.get("card_id"),
                user=pending.get("user"),
            )
            await query.edit_message_text(
                f"✅ Transação registrada!\n"
                f"{pending['description']} — {_fmt_brl(pending['amount'])}"
            )
        except Exception as e:
            log.error("tx_confirm.error", error=str(e))
            await query.edit_message_text("Erro ao salvar transação. Tente novamente.")
