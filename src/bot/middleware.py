"""Aiogram middleware: Telegram ID validation, rate limiting and DB session injection."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser

from src.bot.utils import RateLimiter
from src.config import get_settings
from src.database import crud
from src.database.db import get_db


class AuthRateLimitMiddleware(BaseMiddleware):
    """Rejects updates without a valid user, throttles, and provides ``session``/``db_user``."""

    def __init__(self, limiter: RateLimiter | None = None) -> None:
        self.limiter = limiter or RateLimiter(get_settings().rate_limit_per_minute)

    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject, data: dict[str, Any],
    ) -> Any:
        tg: TgUser | None = data.get("event_from_user")
        if tg is None or tg.is_bot or tg.id <= 0:
            return None
        if not self.limiter.allow(tg.id):
            answer = getattr(event, "answer", None)
            if answer:
                await answer("⏳ Too many requests. Please slow down.")
            return None
        async with get_db().session() as session:
            data["session"] = session
            data["db_user"] = await crud.get_or_create_user(session, tg.id, tg.username)
            return await handler(event, data)
