"""Parse and normalize datetimes from upstream UK sources."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_UK_TZ = ZoneInfo("Europe/London")

# e.g. "13 May 2026, 11:26" (from petrolprices.co.uk live page)
_RE_FEED_UPDATED = re.compile(
    r"Data feed last updated:\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}),\s*(\d{1,2}):(\d{2})",
    re.IGNORECASE,
)

# e.g. "13 May 2026" (from Google Visualization date column)
_RE_DAY_MON_YEAR = re.compile(
    r"^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$",
)


def parse_data_feed_line(html_fragment: str) -> datetime | None:
    """
    Extract ``Data feed last updated: …`` timestamp from the live HTML page.

    Returns timezone-aware datetime in ``Europe/London``, or ``None`` if absent.
    """
    m = _RE_FEED_UPDATED.search(html_fragment)
    if not m:
        return None
    date_part = m.group(1).strip()
    time_h, time_m = int(m.group(2)), int(m.group(3))
    try:
        base = datetime.strptime(date_part, "%d %b %Y").replace(
            hour=time_h,
            minute=time_m,
            tzinfo=_UK_TZ,
        )
        return base
    except ValueError:
        return None


def parse_uk_day_month_year(text: str, *, end_of_day: bool = False) -> datetime | None:
    """
    Parse strings like ``\"13 May 2026\"`` in UK local time.

    When ``end_of_day`` is True, time is set to 23:59:59 (useful if only a date
    is provided and we want a stable ordering vs run time).
    """
    text = text.strip()
    m = _RE_DAY_MON_YEAR.match(text)
    if not m:
        return None
    day, mon, year = int(m.group(1)), m.group(2), int(m.group(3))
    try:
        base = datetime.strptime(f"{day} {mon} {year}", "%d %b %Y")
        if end_of_day:
            base = base.replace(hour=23, minute=59, second=59)
        return base.replace(tzinfo=_UK_TZ)
    except ValueError:
        return None


def to_iso_utc(dt: datetime) -> str:
    """Format as ISO-8601 in UTC with ``Z`` suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
