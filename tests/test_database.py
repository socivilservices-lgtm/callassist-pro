import pytest

from src.database import crud
from src.database.models import SubStatus, Tier
from src.exceptions import NotFoundError


async def test_user_defaults_to_free(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1, "a")
        assert u.subscription.tier == Tier.FREE
        assert (await crud.get_or_create_user(s, 1)).id == u.id
        assert await crud.count_users(s) == 1


async def test_subscription_lifecycle(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 2)
        sub = await crud.set_subscription(s, u, Tier.PRO, "cus", "sub")
        assert sub.tier == Tier.PRO and sub.renews_at
        await crud.cancel_subscription(s, u)
        assert u.subscription.status == SubStatus.CANCELLED and u.subscription.tier == Tier.FREE
        with pytest.raises(NotFoundError):
            await crud.cancel_subscription(s, u)


async def test_calls_usage_audit_gdpr(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 3)
        await crud.add_call_log(s, u.id, "voicemail", "+15551234567")
        await crud.add_call_log(s, u.id, "callback", "+15551234567")
        assert len(await crud.list_call_logs(s, u.id, "voicemail")) == 1
        await crud.record_usage(s, u.id, "m", 10, 5, 0.25)
        assert await crud.total_cost(s, u.id) == 0.25
        assert await crud.count_scripts_today(s, u.id) == 1
        await crud.audit(s, 3, "x")
        assert len(await crud.list_audit(s)) == 1
        await crud.set_voice_preference(s, u, "v1")
        data = await crud.export_user_data(s, 3)
        assert data["voice_preference"] == "v1" and len(data["calls"]) == 2
        assert await crud.delete_user_data(s, 3)
        assert not await crud.delete_user_data(s, 3)
        assert await crud.export_user_data(s, 3) == {}
