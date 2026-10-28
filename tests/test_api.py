import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.config import get_settings
from src.database import crud


@pytest.fixture
async def client(database, monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "sec")
    get_settings.cache_clear()
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://t") as c:
        yield c
    get_settings.cache_clear()


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/openapi.json")).status_code == 200


async def test_admin_auth_and_endpoints(client, database):
    assert (await client.get("/admin/stats")).status_code == 401
    h = {"x-api-key": "k"}
    async with database.session() as s:
        await crud.get_or_create_user(s, 42)
        await crud.audit(s, 42, "a")
    assert (await client.get("/admin/stats", headers=h)).json() == {"users": 1}
    assert len((await client.get("/admin/audit", headers=h)).json()) == 1
    assert (await client.get("/admin/users/42/export", headers=h)).status_code == 200
    assert (await client.delete("/admin/users/42", headers=h)).json() == {"deleted": True}
    assert (await client.delete("/admin/users/42", headers=h)).status_code == 404
    assert (await client.get("/admin/users/42/export", headers=h)).status_code == 404


async def test_webhook_security(client):
    assert (await client.post("/webhook/telegram", json={})).status_code == 403
    r = await client.post("/webhook/telegram", json={}, headers={"x-telegram-bot-api-secret-token": "sec"})
    assert r.status_code == 503
