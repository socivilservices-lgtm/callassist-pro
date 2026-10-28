"""Script generation via OpenAI."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.utils import TIER_FEATURES, tier_allows
from src.database import crud
from src.database.models import User
from src.exceptions import CallAssistError
from src.integrations.elevenlabs_client import TTSClient
from src.integrations.openai_client import OpenAIClient

router = Router()
openai_client = OpenAIClient()
tts_client = TTSClient()


@router.message(Command("script"))
async def script(message: Message, command: CommandObject, session: AsyncSession, db_user: User) -> None:
    if not command.args:
        await message.answer("Usage: /script <situation, e.g. refund request for late delivery>")
        return
    tier = db_user.subscription.tier
    if await crud.count_scripts_today(session, db_user.id) >= TIER_FEATURES[tier]["scripts_per_day"]:
        await message.answer("Daily script limit reached. Upgrade with /plan.")
        return
    try:
        res = await openai_client.generate_script(command.args[:1000])
    except CallAssistError as exc:
        await message.answer(f"⚠️ Could not generate script: {exc}")
        return
    await crud.record_usage(session, db_user.id, res.model, res.prompt_tokens, res.completion_tokens, res.cost_usd)
    await crud.audit(session, message.from_user.id, "script_generated", f"cost={res.cost_usd}")
    await message.answer(res.text)
    if tier_allows(tier, "tts"):
        try:
            audio, _ = await tts_client.synthesize(res.text[:1000], db_user.voice_preference)
            await message.answer_voice(BufferedInputFile(audio, "script.mp3"))
        except CallAssistError:
            pass


@router.message(Command("voice"))
async def voice(message: Message, command: CommandObject, session: AsyncSession, db_user: User) -> None:
    if not command.args:
        await message.answer("Usage: /voice <voice id>")
        return
    await crud.set_voice_preference(session, db_user, command.args.strip()[:64])
    await crud.audit(session, message.from_user.id, "set_voice")
    await message.answer("Voice preference saved.")
