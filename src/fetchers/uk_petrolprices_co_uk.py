"""
Primary UK source: PetrolPrices.co.uk live page (HTML).

The page exposes national averages in stable ``div`` elements and a human
readable ``Data feed last updated`` line. See:
https://petrolprices.co.uk/uk-fuel-prices-live.php
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from src.config import UK_LIVE_PAGE_URL
from src.datetime_util import parse_data_feed_line, to_iso_utc
from src.exceptions import ParseError
from src.http_util import get_text
from src.models import ParsedFuelPrices

if TYPE_CHECKING:
    import httpx

# Fallback if structured divs change: capture first plausible "NNN.Np" after labels.
_RE_PETROL = re.compile(
    r"UK\s*Avg\s*Petrol\s*</div>\s*<div[^>]*figure[^>]*figure-petrol[^>]*>\s*([\d.]+)\s*p",
    re.IGNORECASE | re.DOTALL,
)
_RE_DIESEL = re.compile(
    r"UK\s*Avg\s*Diesel\s*</div>\s*<div[^>]*figure[^>]*figure-diesel[^>]*>\s*([\d.]+)\s*p",
    re.IGNORECASE | re.DOTALL,
)


def _has_figure_class(classes: list[str] | str | None, fragment: str) -> bool:
    if not classes:
        return False
    if isinstance(classes, str):
        classes = classes.split()
    return fragment in classes


def _pence_from_label_soup(soup: BeautifulSoup) -> tuple[float, float]:
    """Walk ``div.label`` nodes and read the adjacent figure sibling."""
    petrol: float | None = None
    diesel: float | None = None
    for label in soup.find_all("div", class_="label"):
        text = label.get_text(strip=True)
        sib = label.find_next_sibling("div")
        if sib is None:
            continue
        sib_classes = sib.get("class") or []
        raw = sib.get_text(strip=True).lower().rstrip("p")
        try:
            val = float(raw)
        except ValueError:
            continue
        if text == "UK Avg Petrol" and _has_figure_class(sib_classes, "figure-petrol"):
            petrol = val
        elif text == "UK Avg Diesel" and _has_figure_class(sib_classes, "figure-diesel"):
            diesel = val
    if petrol is None or diesel is None:
        raise ParseError("Could not locate UK Avg Petrol/Diesel figures in HTML.")
    return petrol, diesel


def _pence_from_regex(html: str) -> tuple[float, float]:
    mp = _RE_PETROL.search(html)
    md = _RE_DIESEL.search(html)
    if not mp or not md:
        raise ParseError("Regex fallback failed for UK live averages.")
    return float(mp.group(1)), float(md.group(1))


def parse_uk_live_html(html: str) -> ParsedFuelPrices:
    """
    Parse petrol/diesel averages and optional feed timestamp from HTML.

    Uses BeautifulSoup first, then a tight regex fallback for resilience.
    """
    soup = BeautifulSoup(html, "html.parser")
    try:
        petrol, diesel = _pence_from_label_soup(soup)
    except ParseError:
        petrol, diesel = _pence_from_regex(html)

    feed_dt = parse_data_feed_line(html)
    last_raw = to_iso_utc(feed_dt) if feed_dt is not None else None

    return ParsedFuelPrices(
        petrol_ppl=petrol,
        diesel_ppl=diesel,
        last_update_raw=last_raw,
        source_url=UK_LIVE_PAGE_URL,
    )


async def fetch_uk_live(client: "httpx.AsyncClient") -> ParsedFuelPrices:
    """Download and parse the UK live page."""
    html = await get_text(client, UK_LIVE_PAGE_URL)
    return parse_uk_live_html(html)
