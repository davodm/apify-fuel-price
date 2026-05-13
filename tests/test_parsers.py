"""Unit tests for HTML/gviz parsers and datetime helpers."""

from __future__ import annotations

import textwrap

import pytest

from src.datetime_util import parse_data_feed_line, parse_uk_day_month_year, to_iso_utc
from src.fetchers.uk_petrolprices_com import parse_gviz_average
from src.fetchers.uk_petrolprices_co_uk import parse_uk_live_html


def test_parse_data_feed_line_extracts_london_timestamp() -> None:
    html = "<p>· Data feed last updated: 13 May 2026, 11:26</p>"
    dt = parse_data_feed_line(html)
    assert dt is not None
    assert "2026-05-13" in to_iso_utc(dt)


def test_parse_uk_day_month_year() -> None:
    dt = parse_uk_day_month_year("13 May 2026")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 13
    iso = to_iso_utc(dt)
    assert iso.endswith("Z")


def test_parse_uk_live_html_minimal_snapshot() -> None:
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
    out = parse_uk_live_html(html)
    assert out.petrol_ppl == 157.9
    assert out.diesel_ppl == 187.2
    assert out.last_update_raw is not None
    assert out.last_update_raw.endswith("Z")


def test_parse_gviz_average_unleaded_sample() -> None:
    body = textwrap.dedent(
        r"""
        /*O_o*/
        google.visualization.Query.setResponse({"version":"0.6","reqId":"0","status":"ok","sig":"772973521","table":{"cols":[{"id":"A","label":"","type":"number","pattern":"General"},{"id":"B","label":"","type":"number","pattern":"General"},{"id":"C","label":"","type":"string"}],"rows":[{"c":[{"v":157.9,"f":"157.9"},{"v":7092.0,"f":"7092"},{"v":"13 May 2026"}]}],"parsedNumHeaders":0}});
        """
    ).strip()
    price, last = parse_gviz_average(body)
    assert price == 157.9
    assert last is not None


def test_parse_gviz_average_last_row_wins() -> None:
    """Ensure parser uses the final row (matches site JS behaviour)."""
    body = textwrap.dedent(
        r"""
        /*O_o*/
        google.visualization.Query.setResponse({"version":"0.6","reqId":"0","status":"ok","table":{"cols":[{"id":"A","type":"number"}],"rows":[
          {"c":[{"v":100.0}]},
          {"c":[{"v":155.5}]}
        ],"parsedNumHeaders":0}});
        """
    ).strip()
    price, _last = parse_gviz_average(body)
    assert price == 155.5


def test_parse_gviz_average_rejects_bad_status() -> None:
    from src.exceptions import ParseError

    body = 'google.visualization.Query.setResponse({"status":"error"});'
    with pytest.raises(ParseError):
        parse_gviz_average(body)
