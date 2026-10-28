"""Handler routers."""
from aiogram import Router

from src.bot.handlers import admin, callbacks, script_gen, start, subscription, voicemail


def get_router() -> Router:
    root = Router()
    root.include_routers(
        start.router, subscription.router, script_gen.router,
        voicemail.router, admin.router, callbacks.router,
    )
    return root
