"""Shared HTTP client helpers."""

from __future__ import annotations

import httpx

from src.config import DEFAULT_TIMEOUT_SECONDS, USER_AGENT
from src.exceptions import UpstreamHttpError


def build_async_client() -> httpx.AsyncClient:
    """Create a configured ``httpx.AsyncClient`` for upstream requests."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(DEFAULT_TIMEOUT_SECONDS),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


async def get_text(client: httpx.AsyncClient, url: str) -> str:
    """GET ``url`` and return response body as text; raise on non-2xx."""
    response = await client.get(url)
    if response.status_code >= 400:
        raise UpstreamHttpError(f"HTTP {response.status_code} for {url!r}")
    return response.text
