from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.bot import utils
from src.bot.handlers import admin, callbacks, script_gen, start, subscription, voicemail
from src.bot.middleware import AuthRateLimitMiddleware
from src.config import get_settings
from src.database import crud
from src.database.models import Tier
from src.integrations.openai_client import ScriptResult


def msg(uid=1, args=None):
    m = SimpleNamespace(from_user=SimpleNamespace(id=uid), answer=AsyncMock(), answer_voice=AsyncMock())
    return m, SimpleNamespace(args=args)


def test_rate_limiter_and_tiers():
    r = utils.RateLimiter(2, 10)
    assert r.allow(1, 0) and r.allow(1, 1) and not r.allow(1, 2) and r.allow(1, 11)
    assert utils.tier_allows(Tier.PRO, "tts") and not utils.tier_allows(Tier.FREE, "tts")


async def test_start_and_gdpr(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1)
        m, _ = msg()
        await start.start(m, s, u)
        await start.help_(m)
        await start.mydata(m, s)
        await start.deleteme(m, s)
        assert m.answer.await_count == 4
        assert await crud.get_user(s, 1) is None


async def test_subscription_flow(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1)
        m, _ = msg()
        await subscription.plan(m, u)
        assert "Subscribed" in await subscription.apply_tier(s, u, Tier.PRO)
        assert u.subscription.tier == Tier.PRO
        assert "cancelled" in await subscription.cancel(s, u)
        assert "no paid" in await subscription.cancel(s, u)
        assert "no paid" in await subscription.apply_tier(s, u, Tier.FREE)


async def test_callbacks(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1)
        for data in ("sub:pro", "sub:bogus", "sub:cancel"):
            cb = SimpleNamespace(data=data, answer=AsyncMock(), message=SimpleNamespace(answer=AsyncMock()))
            await callbacks.on_sub(cb, s, u)
            cb.message.answer.assert_awaited()


async def test_voicemail_handlers(database):
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1)
        m, c = msg(args="+15551234567")
        await voicemail.voicemail(m, c, s, u)
        await voicemail.voicemail(m, SimpleNamespace(args=None), s, u)
        await voicemail.voicemail(m, SimpleNamespace(args="bad"), s, u)
        await voicemail.callback(m, c, s, u)
        await voicemail.callback(m, SimpleNamespace(args="bad"), s, u)
        await voicemail.history(m, s, u)
        assert len(await crud.list_call_logs(s, u.id)) == 2


async def test_script_gen(database, monkeypatch):
    res = ScriptResult("script", "gpt-4o-mini", 10, 10, 0.01)
    monkeypatch.setattr(script_gen.openai_client, "generate_script", AsyncMock(return_value=res))
    monkeypatch.setattr(script_gen.tts_client, "synthesize", AsyncMock(return_value=(b"a", "x")))
    async with database.session() as s:
        u = await crud.get_or_create_user(s, 1)
        m, _ = msg()
        await script_gen.script(m, SimpleNamespace(args=None), s, u)
        for _ in range(3):
            await script_gen.script(m, SimpleNamespace(args="refund"), s, u)
        assert not m.answer_voice.await_count
        await script_gen.script(m, SimpleNamespace(args="refund"), s, u)
        assert "limit" in m.answer.await_args.args[0]
        await crud.set_subscription(s, u, Tier.PRO)
        await script_gen.script(m, SimpleNamespace(args="refund"), s, u)
        assert m.answer_voice.await_count == 1
        await script_gen.voice(m, SimpleNamespace(args="v"), s, u)
        await script_gen.voice(m, SimpleNamespace(args=None), s, u)
        assert u.voice_preference == "v"
        from src.exceptions import IntegrationError
        script_gen.openai_client.generate_script.side_effect = IntegrationError("down")
        await script_gen.script(m, SimpleNamespace(args="x"), s, u)
        assert "Could not" in m.answer.await_args.args[0]


async def test_admin_stats(database, monkeypatch):
    async with database.session() as s:
        m, _ = msg(uid=9)
        await admin.stats(m, s)
        assert "Admins" in m.answer.await_args.args[0]
        monkeypatch.setenv("ADMIN_USER_IDS", "9")
        get_settings.cache_clear()
        await admin.stats(m, s)
        assert "Users" in m.answer.await_args.args[0]
        get_settings.cache_clear()


async def test_middleware(database):
    mw = AuthRateLimitMiddleware(utils.RateLimiter(1))
    handler = AsyncMock(return_value="ok")
    ev = SimpleNamespace(answer=AsyncMock())
    tg = SimpleNamespace(id=5, is_bot=False, username="u")
    assert await mw(handler, ev, {"event_from_user": tg}) == "ok"
    assert await mw(handler, ev, {"event_from_user": tg}) is None
    ev.answer.assert_awaited()
    assert await mw(handler, ev, {}) is None
    assert await mw(handler, ev, {"event_from_user": SimpleNamespace(id=6, is_bot=True)}) is None


def test_dispatcher_builds():
    from src.bot.main import build_dispatcher
    build_dispatcher()
