"""Bot entry point (long polling)."""
from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from src.bot.handlers import get_router
from src.bot.middleware import AuthRateLimitMiddleware
from src.config import get_settings
from src.database.db import get_db
from src.logger import get_logger, setup_logging

log = get_logger(__name__)


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    mw = AuthRateLimitMiddleware()
    dp.message.outer_middleware(mw)
    dp.callback_query.outer_middleware(mw)
    dp.include_router(get_router())
    return dp


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set")
    await get_db().create_all()
    bot = Bot(settings.telegram_bot_token)
    log.info("Starting CallAssist Pro bot")
    try:
        await build_dispatcher().start_polling(bot)
    finally:
        await bot.session.close()
        await get_db().dispose()


if __name__ == "__main__":
    asyncio.run(main())
