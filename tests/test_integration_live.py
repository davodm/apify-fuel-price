"""
Live HTTP checks against real UK endpoints (network required).

Run with the rest of the suite:

    pytest -v

Or with prints:

    pytest -v -s tests/test_integration_live.py
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.integration
def test_live_primary_petrolprices_co_uk_returns_plausible_averages() -> None:
    """Hit petrolprices.co.uk HTML and parse national averages."""
    from src.fetchers.uk_petrolprices_co_uk import fetch_uk_live
    from src.http_util import build_async_client

    async def _run():
        async with build_async_client() as client:
            return await fetch_uk_live(client)

    parsed = asyncio.run(_run())
    assert 80 < parsed.petrol_ppl < 300, f"petrol out of range: {parsed.petrol_ppl}"
    assert 80 < parsed.diesel_ppl < 300, f"diesel out of range: {parsed.diesel_ppl}"
    assert parsed.source_url.startswith("https://")
    print(
        "\n[LIVE primary] petrol={:.1f}p/L diesel={:.1f}p/L last_update_raw={!r}".format(
            parsed.petrol_ppl,
            parsed.diesel_ppl,
            parsed.last_update_raw,
        )
    )


@pytest.mark.integration
def test_live_fallback_petrolprices_com_gviz_returns_plausible_averages() -> None:
    """Hit public gviz endpoints used by petrolprices.com."""
    from src.fetchers.uk_petrolprices_com import fetch_uk_from_gviz_fallback
    from src.http_util import build_async_client

    async def _run():
        async with build_async_client() as client:
            return await fetch_uk_from_gviz_fallback(client)

    parsed = asyncio.run(_run())
    assert 80 < parsed.petrol_ppl < 300
    assert 80 < parsed.diesel_ppl < 300
    print(
        "\n[LIVE gviz] petrol={:.1f}p/L diesel={:.1f}p/L last_update_raw={!r}".format(
            parsed.petrol_ppl,
            parsed.diesel_ppl,
            parsed.last_update_raw,
        )
    )
