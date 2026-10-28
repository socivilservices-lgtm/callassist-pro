"""Voicemail, call history and callback requests (simulated, lawful)."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import crud
from src.database.models import User
from src.exceptions import CallAssistError
from src.integrations.sip_simulator import SIPSimulator

router = Router()
sip = SIPSimulator()


@router.message(Command("voicemail"))
async def voicemail(message: Message, command: CommandObject, session: AsyncSession, db_user: User) -> None:
    if command.args:  # simulate an incoming voicemail notification
        try:
            ev = sip.incoming_voicemail(command.args)
        except CallAssistError as exc:
            await message.answer(str(exc))
            return
        await crud.add_call_log(session, db_user.id, "voicemail", ev.number)
        await crud.audit(session, message.from_user.id, "voicemail_logged", ev.number)
        await message.answer(f"📨 {ev.message}")
        return
    rows = await crud.list_call_logs(session, db_user.id, "voicemail")
    await message.answer("\n".join(f"#{r.id} {r.number} [{r.status}]" for r in rows) or "No voicemails.")


@router.message(Command("callback"))
async def callback(message: Message, command: CommandObject, session: AsyncSession, db_user: User) -> None:
    try:
        ev = sip.request_callback(command.args or "")
    except CallAssistError as exc:
        await message.answer(str(exc))
        return
    await crud.add_call_log(session, db_user.id, "callback", ev.number, "requested")
    await crud.audit(session, message.from_user.id, "callback_requested", ev.number)
    await message.answer(f"📞 {ev.message}")


@router.message(Command("history"))
async def history(message: Message, session: AsyncSession, db_user: User) -> None:
    rows = await crud.list_call_logs(session, db_user.id)
    await message.answer("\n".join(f"{r.kind} {r.number} [{r.status}]" for r in rows) or "No history.")
