"""Admin commands (restricted to ADMIN_USER_IDS)."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import crud

router = Router()


@router.message(Command("stats"))
async def stats(message: Message, session: AsyncSession) -> None:
    if message.from_user.id not in get_settings().admin_ids:
        await message.answer("⛔ Admins only.")
        return
    await message.answer(f"Users: {await crud.count_users(session)}")
