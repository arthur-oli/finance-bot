import os
import structlog
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    filters,
    MessageHandler,
)

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger()

from bot.handlers.commands import (
    cmd_ajuda,
    cmd_assinaturas,
    cmd_forecast,
    cmd_metas,
    cmd_resumo,
    cmd_saldo,
    cmd_start,
)
from bot.handlers.photo import handle_photo, handle_photo_callback
from bot.handlers.text import handle_callback, handle_text

_raw_ids = os.environ.get("TELEGRAM_USER_IDS", os.environ.get("TELEGRAM_USER_ID", ""))
ALLOWED_USER_IDS = [int(x.strip()) for x in _raw_ids.split(",") if x.strip()]


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    auth = filters.User(user_id=ALLOWED_USER_IDS)

    app.add_handler(CommandHandler("start", cmd_start, filters=auth))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda, filters=auth))
    app.add_handler(CommandHandler("saldo", cmd_saldo, filters=auth))
    app.add_handler(CommandHandler("resumo", cmd_resumo, filters=auth))
    app.add_handler(CommandHandler("forecast", cmd_forecast, filters=auth))
    app.add_handler(CommandHandler("metas", cmd_metas, filters=auth))
    app.add_handler(CommandHandler("assinaturas", cmd_assinaturas, filters=auth))

    app.add_handler(MessageHandler(filters.PHOTO & auth, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & auth, handle_text))

    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^tx_"))
    app.add_handler(CallbackQueryHandler(handle_photo_callback, pattern="^photo_"))

    log.info("bot.started", user_ids=ALLOWED_USER_IDS)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
