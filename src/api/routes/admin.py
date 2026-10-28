"""Admin API (requires X-API-Key)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.middleware import require_admin
from src.database import crud
from src.database.db import get_db

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/stats")
async def stats() -> dict[str, int]:
    async with get_db().session() as s:
        return {"users": await crud.count_users(s)}


@router.get("/audit")
async def audit(limit: int = 50) -> list[dict]:
    async with get_db().session() as s:
        rows = await crud.list_audit(s, min(max(limit, 1), 500))
        return [{"id": r.id, "telegram_id": r.telegram_id, "action": r.action, "detail": r.detail,
                 "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/users/{telegram_id}/export")
async def export(telegram_id: int) -> dict:
    async with get_db().session() as s:
        data = await crud.export_user_data(s, telegram_id)
    if not data:
        raise HTTPException(404, "User not found")
    return data


@router.delete("/users/{telegram_id}")
async def delete(telegram_id: int) -> dict[str, bool]:
    async with get_db().session() as s:
        if not await crud.delete_user_data(s, telegram_id):
            raise HTTPException(404, "User not found")
    return {"deleted": True}
