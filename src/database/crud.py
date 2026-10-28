"""CRUD operations."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    AuditLog, CallLog, SubStatus, Subscription, Tier, UsageRecord, User, utcnow,
)
from src.exceptions import NotFoundError


async def get_user(s: AsyncSession, telegram_id: int) -> User | None:
    res = await s.execute(
        select(User).options(selectinload(User.subscription)).where(User.telegram_id == telegram_id)
    )
    return res.scalar_one_or_none()


async def get_or_create_user(s: AsyncSession, telegram_id: int, username: str | None = None) -> User:
    """Fetch the user, creating a Free subscription on first contact."""
    user = await get_user(s, telegram_id)
    if user:
        return user
    user = User(telegram_id=telegram_id, username=username)
    user.subscription = Subscription(tier=Tier.FREE)
    s.add(user)
    await s.flush()
    return user


async def set_voice_preference(s: AsyncSession, user: User, voice: str) -> None:
    user.voice_preference = voice
    await s.flush()


async def set_subscription(
    s: AsyncSession, user: User, tier: Tier, customer_id: str | None = None,
    subscription_id: str | None = None, days: int = 30,
) -> Subscription:
    sub = user.subscription or Subscription(user_id=user.id)
    sub.tier = tier
    sub.status = SubStatus.ACTIVE
    sub.stripe_customer_id = customer_id or sub.stripe_customer_id
    sub.stripe_subscription_id = subscription_id or sub.stripe_subscription_id
    sub.renews_at = None if tier == Tier.FREE else utcnow() + timedelta(days=days)
    sub.updated_at = utcnow()
    user.subscription = sub
    s.add(sub)
    await s.flush()
    return sub


async def cancel_subscription(s: AsyncSession, user: User) -> Subscription:
    sub = user.subscription
    if sub is None or sub.tier == Tier.FREE:
        raise NotFoundError("No paid subscription to cancel")
    sub.status = SubStatus.CANCELLED
    sub.tier = Tier.FREE
    sub.renews_at = None
    sub.updated_at = utcnow()
    await s.flush()
    return sub


async def add_call_log(s: AsyncSession, user_id: int, kind: str, number: str, note: str | None = None) -> CallLog:
    row = CallLog(user_id=user_id, kind=kind, number=number, note=note)
    s.add(row)
    await s.flush()
    return row


async def list_call_logs(s: AsyncSession, user_id: int, kind: str | None = None, limit: int = 10) -> list[CallLog]:
    q = select(CallLog).where(CallLog.user_id == user_id)
    if kind:
        q = q.where(CallLog.kind == kind)
    res = await s.execute(q.order_by(CallLog.id.desc()).limit(limit))
    return list(res.scalars())


async def record_usage(
    s: AsyncSession, user_id: int, model: str, prompt_tokens: int, completion_tokens: int, cost: float
) -> UsageRecord:
    row = UsageRecord(
        user_id=user_id, model=model, prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens, cost_usd=cost,
    )
    s.add(row)
    await s.flush()
    return row


async def total_cost(s: AsyncSession, user_id: int) -> float:
    res = await s.execute(select(func.coalesce(func.sum(UsageRecord.cost_usd), 0.0)).where(UsageRecord.user_id == user_id))
    return float(res.scalar_one())


async def count_scripts_today(s: AsyncSession, user_id: int) -> int:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    res = await s.execute(
        select(func.count(UsageRecord.id)).where(UsageRecord.user_id == user_id, UsageRecord.created_at >= start)
    )
    return int(res.scalar_one())


async def audit(s: AsyncSession, telegram_id: int | None, action: str, detail: str | None = None) -> None:
    s.add(AuditLog(telegram_id=telegram_id, action=action, detail=detail))
    await s.flush()


async def list_audit(s: AsyncSession, limit: int = 50) -> list[AuditLog]:
    res = await s.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))
    return list(res.scalars())


async def count_users(s: AsyncSession) -> int:
    return int((await s.execute(select(func.count(User.id)))).scalar_one())


async def delete_user_data(s: AsyncSession, telegram_id: int) -> bool:
    """GDPR erasure: remove the user and all linked records (audit rows anonymised)."""
    user = await get_user(s, telegram_id)
    if not user:
        return False
    await s.execute(delete(CallLog).where(CallLog.user_id == user.id))
    await s.execute(delete(UsageRecord).where(UsageRecord.user_id == user.id))
    await s.execute(delete(AuditLog).where(AuditLog.telegram_id == telegram_id))
    await s.delete(user)
    await s.flush()
    return True


async def export_user_data(s: AsyncSession, telegram_id: int) -> dict:
    """GDPR export of everything stored about a user."""
    user = await get_user(s, telegram_id)
    if not user:
        return {}
    logs = await list_call_logs(s, user.id, limit=1000)
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "voice_preference": user.voice_preference,
        "tier": user.subscription.tier.value if user.subscription else None,
        "calls": [{"kind": c.kind, "number": c.number, "status": c.status, "note": c.note} for c in logs],
        "total_ai_cost_usd": await total_cost(s, user.id),
    }
