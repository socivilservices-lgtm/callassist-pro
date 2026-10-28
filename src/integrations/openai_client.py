"""OpenAI wrapper for customer-service script generation with cost tracking."""
from __future__ import annotations

from dataclasses import dataclass

from src.config import Settings, get_settings
from src.exceptions import IntegrationError

SYSTEM_PROMPT = (
    "You are an assistant for customer support staff. Write clear, polite, honest call scripts. "
    "Never impersonate others, spoof identities, or request passwords, OTP codes or 2FA tokens."
)


@dataclass
class ScriptResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class OpenAIClient:
    """Thin async wrapper around the OpenAI chat completions API."""

    def __init__(self, settings: Settings | None = None, client=None) -> None:
        self.settings = settings or get_settings()
        self._client = client

    def _get_client(self):
        if self._client is None:
            if not self.settings.openai_api_key:
                raise IntegrationError("OPENAI_API_KEY is not configured")
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        s = self.settings
        return round(
            prompt_tokens / 1000 * s.openai_input_cost_per_1k
            + completion_tokens / 1000 * s.openai_output_cost_per_1k,
            6,
        )

    async def generate_script(
        self, prompt: str, context: str | None = None,
        temperature: float | None = None, max_tokens: int | None = None,
    ) -> ScriptResult:
        """Generate a script; raises :class:`IntegrationError` on API failure."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": f"Context: {context}"})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = await self._get_client().chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                temperature=self.settings.openai_temperature if temperature is None else temperature,
                max_tokens=max_tokens or self.settings.openai_max_tokens,
            )
        except IntegrationError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise provider errors
            raise IntegrationError(f"OpenAI request failed: {exc}") from exc
        usage = resp.usage
        pt, ct = (usage.prompt_tokens, usage.completion_tokens) if usage else (0, 0)
        return ScriptResult(
            text=(resp.choices[0].message.content or "").strip(),
            model=self.settings.openai_model,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_usd=self.estimate_cost(pt, ct),
        )
