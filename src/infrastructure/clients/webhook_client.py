from typing import Any

import httpx


class WebhookClient:
    def __init__(self, timeout_seconds: int) -> None:
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def post_json(self, url: str, payload: dict[str, Any]) -> None:
        response = await self._client.post(url, json=payload)
        response.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
