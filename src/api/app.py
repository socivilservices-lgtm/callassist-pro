"""FastAPI application (OpenAPI docs at /docs)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import log_requests
from src.api.routes import admin, health, webhook
from src.config import get_settings
from src.database.db import get_db
from src.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    await get_db().create_all()
    if settings.telegram_bot_token:
        from aiogram import Bot

        from src.bot.main import build_dispatcher

        app.state.bot = Bot(settings.telegram_bot_token)
        app.state.dispatcher = build_dispatcher()
        if settings.telegram_webhook_url:
            await app.state.bot.set_webhook(
                settings.telegram_webhook_url, secret_token=settings.telegram_webhook_secret or None
            )
    yield
    if getattr(app.state, "bot", None):
        await app.state.bot.session.close()
    await get_db().dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="CallAssist Pro API", version="1.0.0", lifespan=lifespan)
    app.middleware("http")(log_requests)
    app.include_router(health.router)
    app.include_router(webhook.router)
    app.include_router(admin.router)
    return app


app = create_app()
