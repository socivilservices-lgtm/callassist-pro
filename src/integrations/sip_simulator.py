"""Lawful SIP simulation.

Only logs/notifies about calls. It never sets or alters caller ID and never places
real calls, so spoofing is structurally impossible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from src.exceptions import CallAssistError

_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def validate_number(number: str) -> str:
    """Normalise and validate an E.164 phone number."""
    cleaned = re.sub(r"[\s\-().]", "", number or "")
    if not _E164.match(cleaned):
        raise CallAssistError("Phone number must be in E.164 format, e.g. +15551234567")
    return cleaned


@dataclass
class SimulatedEvent:
    kind: str
    number: str
    message: str


class SIPSimulator:
    """Simulates inbound-call notifications; caller ID is always the real, supplied number."""

    def incoming_voicemail(self, number: str) -> SimulatedEvent:
        n = validate_number(number)
        return SimulatedEvent("voicemail", n, f"New voicemail from {n}")

    def request_callback(self, number: str) -> SimulatedEvent:
        n = validate_number(number)
        return SimulatedEvent("callback", n, f"Callback to {n} queued (simulated, no call placed)")

    def log_call(self, number: str) -> SimulatedEvent:
        n = validate_number(number)
        return SimulatedEvent("call", n, f"Call with {n} logged")
