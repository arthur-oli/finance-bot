from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
import structlog
from bot.services import backend_client as bc

log = structlog.get_logger()


def _fmt_brl(v) -> str:
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


_WELCOME = (
    "👋 *Olá! Sou seu bot financeiro.*\n"
    "Te ajudo a registrar gastos e receitas direto pelo Telegram.\n\n"
    "━━━━━━━━━━━━━━━\n"
    "📝 *Maneira mais simples: me mande uma mensagem*\n\n"
    "Escreva naturalmente, eu entendo. Exemplos:\n"
    "• `gastei 45 no mercado`\n"
    "• `45 reais de uber`\n"
    "• `recebi 3000 de salário`\n"
    "• `comprei tênis por 280 no nubank`\n"
    "• `100 de farmácia hoje, deborah pagou`\n\n"
    "Eu identifico automaticamente:\n"
    "💸 valor • 🏷️ categoria • 💳 cartão • 👤 pessoa • 📅 data\n\n"
    "━━━━━━━━━━━━━━━\n"
    "📸 *Mandou foto de comprovante?*\n"
    "Funciona também! Tira foto do recibo/nota e envia.\n"
    "Notas com vários itens (mercado, farmácia) eu separo por categoria.\n\n"
    "━━━━━━━━━━━━━━━\n"
    "📊 *Comandos diretos:*\n"
    "/saldo — receitas, despesas e saldo do mês\n"
    "/resumo — últimas 5 transações\n"
    "/forecast — previsão até o fim do mês\n"
    "/metas — progresso das suas metas\n"
    "/assinaturas — assinaturas ativas e custo mensal\n"
    "/ajuda — esta mensagem\n\n"
    "━━━━━━━━━━━━━━━\n"
    "🌐 *No painel web você pode:*\n"
    "• Cadastrar e editar cartões (com limite, fechamento, vencimento)\n"
    "• Criar metas (ex: viagem, reserva de emergência)\n"
    "• Cadastrar assinaturas recorrentes\n"
    "• Editar/excluir transações\n"
    "• Ver gráficos por categoria e mês\n"
    "• Personalizar categorias\n\n"
    "💡 *Dica:* cadastre seus cartões no painel antes de usar — assim eu reconheço quando você falar deles."
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(_WELCOME, parse_mode="Markdown")


async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


async def cmd_saldo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = bc.get_balance_summary()
        summary = data["summary"]
        inc = _fmt_brl(summary["total_income"])
        exp = _fmt_brl(summary["total_expenses"])
        bal = _fmt_brl(summary["balance"])
        month = date.today().strftime("%B/%Y")

        text = (
            f"📊 *Resumo de {month}*\n\n"
            f"✅ Receitas: {inc}\n"
            f"❌ Despesas: {exp}\n"
            f"💰 Saldo: {bal}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error("cmd_saldo.error", error=str(e))
        await update.message.reply_text("Erro ao buscar saldo. Tente novamente.")


async def cmd_resumo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = bc.list_transactions(limit=5)
        items = data.get("items", [])
        if not items:
            await update.message.reply_text("Nenhuma transação encontrada.")
            return

        lines = ["📋 *Últimas transações:*\n"]
        for t in items:
            icon = "✅" if t["type"] == "income" else "❌"
            lines.append(f"{icon} {t['date']} — {t['description']}: {_fmt_brl(t['amount'])}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error("cmd_resumo.error", error=str(e))
        await update.message.reply_text("Erro ao buscar transações.")


async def cmd_forecast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = bc.get_forecast()
        month = data["month"]
        proj_inc = _fmt_brl(data["projected_income"])
        proj_exp = _fmt_brl(data["projected_expenses"])
        proj_bal = _fmt_brl(data["projected_balance"])
        subs = _fmt_brl(data["subscriptions_total"])
        pace = float(data["pace_factor"]) * 100

        text = (
            f"🔮 *Previsão para {month}*\n\n"
            f"📈 Receitas previstas: {proj_inc}\n"
            f"📉 Despesas previstas: {proj_exp}\n"
            f"📋 Assinaturas: {subs}\n"
            f"💰 Saldo previsto: {proj_bal}\n\n"
            f"📅 Ritmo do mês: {pace:.0f}%"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error("cmd_forecast.error", error=str(e))
        await update.message.reply_text("Erro ao buscar previsão.")


async def cmd_metas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        goals = bc.list_goals()
        if not goals:
            await update.message.reply_text("Nenhuma meta cadastrada. Crie uma no dashboard.")
            return

        lines = ["🎯 *Suas metas:*\n"]
        for g in goals:
            pct = (float(g["current_amount"]) / float(g["target_amount"]) * 100) if float(g["target_amount"]) > 0 else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            lines.append(
                f"*{g['name']}*\n"
                f"{bar} {pct:.0f}%\n"
                f"{_fmt_brl(g['current_amount'])} / {_fmt_brl(g['target_amount'])}\n"
            )

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error("cmd_metas.error", error=str(e))
        await update.message.reply_text("Erro ao buscar metas.")


async def cmd_assinaturas(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        subs = bc.list_subscriptions()
        if not subs:
            await update.message.reply_text("Nenhuma assinatura cadastrada.")
            return

        total = sum(
            float(s["amount"]) if s["frequency"] == "monthly" else float(s["amount"]) / 12
            for s in subs
        )
        lines = [f"📌 *Assinaturas ativas ({_fmt_brl(total)}/mês):*\n"]
        for s in subs:
            freq = "mensal" if s["frequency"] == "monthly" else "anual"
            lines.append(f"• {s['name']}: {_fmt_brl(s['amount'])} ({freq})")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error("cmd_assinaturas.error", error=str(e))
        await update.message.reply_text("Erro ao buscar assinaturas.")
