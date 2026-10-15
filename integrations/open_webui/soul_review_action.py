"""
title: Review Evolving Soul Memory
author: Evolving Soul AI contributors
version: 3.0.0a1
required_open_webui_version: 0.11.2
requirements: httpx>=0.27,<1
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field


class Action:
    class Valves(BaseModel):
        sidecar_url: str = "http://host.docker.internal:8765"
        timeout_seconds: float = 2.0

    class UserValves(BaseModel):
        pairing_token: str = Field(
            default="", json_schema_extra={"input": {"type": "password"}}
        )

    def __init__(self) -> None:
        self.valves = self.Valves()

    async def action(
        self,
        body: dict[str, Any],
        __user__: dict[str, Any] | None = None,
        __event_emitter__: Any = None,
    ) -> dict[str, Any]:
        user_id = str((__user__ or {}).get("id", ""))
        token = getattr((__user__ or {}).get("valves"), "pairing_token", "")
        if not token or not user_id:
            return {"error": "Pair Evolving Soul for this Open WebUI user first."}
        try:
            async with httpx.AsyncClient(timeout=self.valves.timeout_seconds) as client:
                response = await client.post(
                    self.valves.sidecar_url.rstrip("/") + "/v1/review-link",
                    json={"proposal_id": body.get("id", "queue")},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Open-WebUI-User-Id": user_id,
                    },
                )
                response.raise_for_status()
            link = response.json()["url"]
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "notification",
                        "data": {"type": "info", "content": f"Review locally: {link}"},
                    }
                )
            return {"review_url": link, "requires_passkey": True}
        except Exception:
            return {"error": "Local sidecar unavailable; no approval action was performed."}
