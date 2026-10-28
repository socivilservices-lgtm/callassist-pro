from types import SimpleNamespace

import httpx
import pytest

from src.config import Settings
from src.database.models import Tier
from src.exceptions import CallAssistError, IntegrationError
from src.integrations.elevenlabs_client import TTSClient
from src.integrations.openai_client import OpenAIClient
from src.integrations.sip_simulator import SIPSimulator, validate_number
from src.integrations.stripe_client import MockStripe


class FakeCompletions:
    async def create(self, **kw):
        assert kw["model"] == "gpt-4o-mini"
        msg = SimpleNamespace(content=" hello ")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg)],
            usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=1000),
        )


async def test_openai_script_and_cost():
    fake = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    c = OpenAIClient(Settings(openai_api_key="k"), client=fake)
    r = await c.generate_script("p", context="ctx", temperature=0.1, max_tokens=10)
    assert r.text == "hello" and r.cost_usd == pytest.approx(0.00075)


async def test_openai_errors():
    with pytest.raises(IntegrationError):
        await OpenAIClient(Settings(openai_api_key="")).generate_script("x")

    class Boom:
        async def create(self, **kw):
            raise RuntimeError("x")

    c = OpenAIClient(Settings(), client=SimpleNamespace(chat=SimpleNamespace(completions=Boom())))
    with pytest.raises(IntegrationError):
        await c.generate_script("x")


async def test_tts_elevenlabs_ok():
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"mp3")))
    audio, prov = await TTSClient(Settings(elevenlabs_api_key="k"), http).synthesize("hi")
    assert (audio, prov) == (b"mp3", "elevenlabs")


async def test_tts_fallback_to_polly(monkeypatch):
    http = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    c = TTSClient(Settings(elevenlabs_api_key="k"), http)

    async def polly(text, voice):
        return b"p"

    monkeypatch.setattr(c, "_polly", polly)
    assert await c.synthesize("hi") == (b"p", "polly")
    with pytest.raises(IntegrationError):
        await TTSClient(Settings(elevenlabs_api_key=""))._elevenlabs("hi", "v")


def test_sip_simulator():
    s = SIPSimulator()
    assert validate_number("+1 (555) 123-4567") == "+15551234567"
    assert "voicemail" in s.incoming_voicemail("+15551234567").message
    assert s.request_callback("+15551234567").kind == "callback"
    assert s.log_call("+15551234567").kind == "call"
    with pytest.raises(CallAssistError):
        validate_number("abc")


def test_mock_stripe():
    st = MockStripe()
    cus, sub = st.subscribe(5, Tier.PRO)
    assert st.payments[0].amount_usd == 19 and cus == "cus_mock_5"
    assert st.cancel(sub) and not st.cancel("nope")
