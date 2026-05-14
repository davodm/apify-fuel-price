"""
Offline contract test: dataset payload matches what ``Actor.push_data`` uses.

Run with ``-s`` to print a sample JSON object (same keys/types as on Apify):

    pytest -v -s tests/test_actor_output_contract.py
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime, timezone

from src.config import COUNTRY_OUTPUT_PRICING
from src.datetime_util import to_iso_utc
from src.fetchers.uk_petrolprices_co_uk import parse_uk_live_html
from src.models import ActorOutputRecord


def test_dataset_payload_matches_apify_push_data_contract() -> None:
    """Build ``ActorOutputRecord`` from parsed HTML; assert keys and UK pricing semantics."""
    html = textwrap.dedent(
        """
        <html><body>
        <div class="label">UK Avg Petrol</div>
        <div class="figure figure-petrol">157.9p</div>
        <div class="label">UK Avg Diesel</div>
        <div class="figure figure-diesel">187.2p</div>
        <p>· Data feed last updated: 13 May 2026, 10:03                </p>
        </body></html>
        """
    )
    parsed = parse_uk_live_html(html)
    fetched_fixed = to_iso_utc(datetime(2026, 5, 13, 12, 0, 0, tzinfo=timezone.utc))
    last = parsed.last_update_raw or fetched_fixed
    pricing = COUNTRY_OUTPUT_PRICING["uk"]

    record = ActorOutputRecord(
        country="uk",
        petrol=round(parsed.petrol_ppl / 100, 3),
        diesel=round(parsed.diesel_ppl / 100, 3),
        lastUpdate=last,
        currency=pricing["currency"],
        volumeUnit=pricing["volumeUnit"],
    )
    payload = record.to_push_dict()

    assert set(payload) == {
        "country",
        "petrol",
        "diesel",
        "lastUpdate",
        "currency",
        "volumeUnit",
    }
    assert payload["country"] == "uk"
    assert payload["currency"] == "GBP"
    assert payload["volumeUnit"] == "litre"
    assert payload["petrol"] == 1.579
    assert payload["diesel"] == 1.872
    assert isinstance(payload["petrol"], float)
    assert isinstance(payload["diesel"], float)

    # Visible with: pytest -s tests/test_actor_output_contract.py
    print("\n=== Example dataset item (Apify default dataset / push_data) ===\n")
    print(json.dumps(payload, indent=2))
    print()
