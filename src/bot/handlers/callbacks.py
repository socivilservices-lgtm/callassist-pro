"""Inline button callbacks."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.subscription import apply_tier, cancel
from src.database.models import Tier, User

router = Router()


@router.callback_query(F.data.startswith("sub:"))
async def on_sub(cb: CallbackQuery, session: AsyncSession, db_user: User) -> None:
    choice = cb.data.split(":", 1)[1]
    if choice == "cancel":
        text = await cancel(session, db_user)
    else:
        try:
            text = await apply_tier(session, db_user, Tier(choice))
        except ValueError:
            text = "Unknown plan."
    await cb.answer()
    if cb.message:
        await cb.message.answer(text)
