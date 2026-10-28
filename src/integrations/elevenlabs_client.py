"""Text-to-speech: ElevenLabs primary, Amazon Polly fallback."""
from __future__ import annotations

import asyncio

import httpx

from src.config import Settings, get_settings
from src.exceptions import IntegrationError
from src.logger import get_logger

log = get_logger(__name__)
API = "https://api.elevenlabs.io/v1/text-to-speech"


class TTSClient:
    """Synthesises speech, falling back to Polly when ElevenLabs is unavailable."""

    def __init__(self, settings: Settings | None = None, http: httpx.AsyncClient | None = None) -> None:
        self.settings = settings or get_settings()
        self._http = http

    async def _elevenlabs(self, text: str, voice: str) -> bytes:
        if not self.settings.elevenlabs_api_key:
            raise IntegrationError("ELEVENLABS_API_KEY is not configured")
        client = self._http or httpx.AsyncClient(timeout=30)
        try:
            r = await client.post(
                f"{API}/{voice}",
                headers={"xi-api-key": self.settings.elevenlabs_api_key, "accept": "audio/mpeg"},
                json={"text": text},
            )
            r.raise_for_status()
            return r.content
        except httpx.HTTPError as exc:
            raise IntegrationError(f"ElevenLabs failed: {exc}") from exc
        finally:
            if self._http is None:
                await client.aclose()

    async def _polly(self, text: str, voice: str) -> bytes:
        try:
            import boto3  # optional dependency
        except ImportError as exc:
            raise IntegrationError("Polly fallback requires boto3") from exc

        def call() -> bytes:
            polly = boto3.client("polly", region_name=self.settings.aws_region)
            out = polly.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId=voice)
            return out["AudioStream"].read()

        try:
            return await asyncio.to_thread(call)
        except Exception as exc:  # noqa: BLE001
            raise IntegrationError(f"Polly failed: {exc}") from exc

    async def synthesize(self, text: str, voice: str | None = None) -> tuple[bytes, str]:
        """Return ``(audio_bytes, provider)``."""
        try:
            return await self._elevenlabs(text, voice or self.settings.elevenlabs_default_voice), "elevenlabs"
        except IntegrationError as exc:
            log.warning("ElevenLabs unavailable, trying Polly: %s", exc)
        return await self._polly(text, self.settings.polly_default_voice), "polly"
