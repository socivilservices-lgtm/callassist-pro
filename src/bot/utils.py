"""Helpers: tier features and rate limiting."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from src.database.models import Tier

TIER_FEATURES: dict[Tier, dict] = {
    Tier.FREE: {"scripts_per_day": 3, "tts": False, "voicemail": True},
    Tier.PRO: {"scripts_per_day": 100, "tts": True, "voicemail": True},
    Tier.ENTERPRISE: {"scripts_per_day": 10_000, "tts": True, "voicemail": True},
}


def tier_allows(tier: Tier, feature: str) -> bool:
    return bool(TIER_FEATURES[tier].get(feature))


class RateLimiter:
    """Sliding-window per-user limiter."""

    def __init__(self, limit: int, window: float = 60.0) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        q = self._hits[user_id]
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
