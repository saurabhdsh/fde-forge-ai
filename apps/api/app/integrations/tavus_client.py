"""Tavus Conversational Video Interface HTTP client."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError, ValidationAppError
from app.core.logging import get_logger

logger = get_logger(__name__)

TAVUS_BASE = "https://tavusapi.com"


class TavusClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _headers(self) -> dict[str, str]:
        if not self.settings.tavus_configured:
            raise ConfigurationError(
                "TAVUS_API_KEY is not configured. Set TAVUS_API_KEY to enable live interviews."
            )
        return {
            "Content-Type": "application/json",
            "x-api-key": self.settings.tavus_api_key.strip(),
        }

    async def create_conversation(
        self,
        *,
        conversation_name: str,
        conversational_context: str,
        callback_url: str | None = None,
        test_mode: bool = False,
        max_call_duration: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "conversation_name": conversation_name[:100],
            "conversational_context": conversational_context[:10000],
            "test_mode": test_mode,
            "properties": {
                "max_call_duration": max_call_duration
                or self.settings.tavus_max_call_duration_seconds,
            },
        }
        pal_id = (self.settings.tavus_pal_id or "").strip()
        face_id = (self.settings.tavus_face_id or "").strip()
        if pal_id:
            body["pal_id"] = pal_id
            # Legacy alias still accepted by Tavus
            body["persona_id"] = pal_id
        if face_id:
            body["face_id"] = face_id
            body["replica_id"] = face_id
        if not pal_id and not face_id:
            raise ConfigurationError(
                "Configure TAVUS_PAL_ID and/or TAVUS_FACE_ID for live interviews."
            )
        if callback_url:
            body["callback_url"] = callback_url

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{TAVUS_BASE}/v2/conversations",
                headers=self._headers(),
                json=body,
            )
        data = self._parse(response)
        if not response.is_success:
            logger.error("tavus_create_failed", status=response.status_code, body=data)
            raise ValidationAppError(
                data.get("error")
                or data.get("message")
                or f"Tavus conversation create failed ({response.status_code})",
                details={"tavus": data},
            )
        return data

    async def end_conversation(self, conversation_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TAVUS_BASE}/v2/conversations/{conversation_id}/end",
                headers=self._headers(),
            )
        if response.status_code in {200, 204}:
            return
        data = self._parse(response)
        # Already ended is fine
        if response.status_code == 400 and "ended" in str(data).lower():
            return
        logger.warning("tavus_end_failed", status=response.status_code, body=data)

    async def get_conversation(
        self, conversation_id: str, *, verbose: bool = True
    ) -> dict[str, Any]:
        params = {"verbose": "true"} if verbose else None
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{TAVUS_BASE}/v2/conversations/{conversation_id}",
                headers=self._headers(),
                params=params,
            )
        data = self._parse(response)
        if not response.is_success:
            raise ValidationAppError(
                data.get("error")
                or data.get("message")
                or f"Tavus get conversation failed ({response.status_code})",
                details={"tavus": data},
            )
        return data

    @staticmethod
    def extract_transcript(payload: dict[str, Any]) -> list[dict[str, Any]]:
        events = payload.get("events") or []
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") != "application.transcription_ready":
                continue
            props = event.get("properties") or {}
            raw = props.get("transcript") or []
            turns: list[dict[str, Any]] = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                content = (item.get("content") or "").strip()
                role = (item.get("role") or "user").strip()
                if not content:
                    continue
                turns.append(
                    {
                        "role": role,
                        "content": content,
                        "timestamp": item.get("timestamp"),
                        "seconds_from_start": item.get("seconds_from_start"),
                    }
                )
            return turns
        return []

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        except Exception:
            return {"raw": response.text[:2000]}
