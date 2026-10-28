"""Telegram webhook endpoint."""
from __future__ import annotations

import hmac

from aiogram import Bot
from aiogram.types import Update
from fastapi import APIRouter, Header, HTTPException, Request

from src.config import get_settings

router = APIRouter(tags=["webhook"])


@router.post("/webhook/telegram")
async def telegram_webhook(
    request: Request, x_telegram_bot_api_secret_token: str = Header(default="")
) -> dict[str, bool]:
    settings = get_settings()
    secret = settings.telegram_webhook_secret
    if not secret or not hmac.compare_digest(x_telegram_bot_api_secret_token, secret):
        raise HTTPException(status_code=403, detail="Forbidden")
    dp = getattr(request.app.state, "dispatcher", None)
    bot: Bot | None = getattr(request.app.state, "bot", None)
    if dp is None or bot is None:
        raise HTTPException(status_code=503, detail="Bot not initialised")
    await dp.feed_update(bot, Update.model_validate(await request.json(), context={"bot": bot}))
    return {"ok": True}
