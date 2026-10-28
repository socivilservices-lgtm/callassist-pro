"""API middleware: request logging and admin key dependency."""
from __future__ import annotations

import hmac
import time

from fastapi import Header, HTTPException, Request

from src.config import get_settings
from src.logger import get_logger

log = get_logger("api")


async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("unhandled error on %s", request.url.path)
        raise
    log.info("%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


async def require_admin(x_api_key: str = Header(default="")) -> None:
    key = get_settings().admin_api_key
    if not key or not hmac.compare_digest(x_api_key, key):
        raise HTTPException(status_code=401, detail="Invalid API key")
