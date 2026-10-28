"""/start, /help and GDPR commands."""
from __future__ import annotations

import json

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import crud
from src.database.models import User

router = Router()


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession, db_user: User) -> None:
    await crud.audit(session, message.from_user.id, "start")
    await message.answer(
        "👋 Welcome to CallAssist Pro!\n\n"
        "/script <topic> – generate a support script\n/voicemail – voicemails\n"
        "/callback <number> – request a callback\n/plan – subscription\n"
        "/mydata – export your data\n/deleteme – erase your data\n\n"
        "All actions are logged. No caller-ID spoofing, no credential or OTP collection."
    )


@router.message(Command("help"))
async def help_(message: Message) -> None:
    await message.answer("Use /start to see available commands.")


@router.message(Command("mydata"))
async def mydata(message: Message, session: AsyncSession) -> None:
    data = await crud.export_user_data(session, message.from_user.id)
    await crud.audit(session, message.from_user.id, "export_data")
    await message.answer(f"<pre>{json.dumps(data, indent=2)}</pre>", parse_mode="HTML")


@router.message(Command("deleteme"))
async def deleteme(message: Message, session: AsyncSession) -> None:
    await crud.delete_user_data(session, message.from_user.id)
    await crud.audit(session, None, "user_erased", "gdpr deletion")
    await message.answer("🗑️ Your data has been deleted.")
