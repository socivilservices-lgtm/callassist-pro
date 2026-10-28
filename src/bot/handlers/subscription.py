"""Subscription management."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import crud
from src.database.models import Tier, User
from src.exceptions import NotFoundError
from src.integrations.stripe_client import PRICES_USD, stripe_client

router = Router()


def plan_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{t.value.title()} (${PRICES_USD[t]}/mo)", callback_data=f"sub:{t.value}")]
        for t in Tier
    ]
    rows.append([InlineKeyboardButton(text="Cancel subscription", callback_data="sub:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def apply_tier(session: AsyncSession, user: User, tier: Tier) -> str:
    """Change tier (mock payment for paid tiers). Returns user-facing text."""
    if tier == Tier.FREE:
        return await cancel(session, user)
    cus, sub = stripe_client.subscribe(user.telegram_id, tier)
    await crud.set_subscription(session, user, tier, cus, sub)
    await crud.audit(session, user.telegram_id, "subscribe", tier.value)
    return f"✅ Subscribed to {tier.value.title()} (mock payment)."


async def cancel(session: AsyncSession, user: User) -> str:
    sub_id = user.subscription.stripe_subscription_id if user.subscription else None
    try:
        await crud.cancel_subscription(session, user)
    except NotFoundError:
        return "You have no paid subscription."
    stripe_client.cancel(sub_id)
    await crud.audit(session, user.telegram_id, "cancel_subscription")
    return "Subscription cancelled; you are now on Free."


@router.message(Command("plan"))
async def plan(message: Message, db_user: User) -> None:
    tier = db_user.subscription.tier.value if db_user.subscription else "free"
    await message.answer(f"Current plan: {tier.title()}", reply_markup=plan_keyboard())
