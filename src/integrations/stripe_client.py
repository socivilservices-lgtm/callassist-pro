"""Mock Stripe client: in-memory payment tracking, no network calls."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from src.database.models import Tier

PRICES_USD = {Tier.FREE: 0, Tier.PRO: 19, Tier.ENTERPRISE: 99}


@dataclass
class MockPayment:
    id: str
    customer_id: str
    amount_usd: int
    tier: Tier
    status: str = "succeeded"


@dataclass
class MockStripe:
    payments: list[MockPayment] = field(default_factory=list)
    subscriptions: dict[str, str] = field(default_factory=dict)

    def create_customer(self, telegram_id: int) -> str:
        return f"cus_mock_{telegram_id}"

    def subscribe(self, telegram_id: int, tier: Tier) -> tuple[str, str]:
        """Create a (fake) paid subscription; returns ``(customer_id, subscription_id)``."""
        cus = self.create_customer(telegram_id)
        sub = f"sub_mock_{uuid.uuid4().hex[:12]}"
        self.subscriptions[sub] = "active"
        self.payments.append(MockPayment(f"pi_mock_{uuid.uuid4().hex[:12]}", cus, PRICES_USD[tier], tier))
        return cus, sub

    def cancel(self, subscription_id: str | None) -> bool:
        if subscription_id and subscription_id in self.subscriptions:
            self.subscriptions[subscription_id] = "cancelled"
            return True
        return False


stripe_client = MockStripe()
