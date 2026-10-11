"""Text at the edges: input in (ADR 0006), numbers and times out (ADR 0003).

Stored instants are UTC; a person's time zone is applied only when a page is drawn. A language
profile (see `foundation/profiles/`) replaces this file and keeps its public names
(`normalize_digits`, `utc_now`, `template_filters`), so nothing else in the app changes.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# Extra arguments for the design system's `install()` when build-spec copies it in (a language
# profile sets lang, direction and calendar here).
DS_OPTIONS: dict[str, str] = {}


def normalize_digits(value: str) -> str:
    """Any script's decimal digits to ASCII, composed and trimmed — once, where input arrives."""
    composed = unicodedata.normalize("NFC", value)
    return "".join(
        str(unicodedata.decimal(ch)) if unicodedata.category(ch) == "Nd" else ch for ch in composed
    ).strip()


def format_number(value: object) -> str:
    """An integer with thousands separators; anything else as it is."""
    return f"{value:,}" if isinstance(value, int) else str(value)


def template_filters(zone_name: str) -> dict[str, Callable[..., str]]:
    """The two filters every template uses: `number` and `local`. An empty zone means UTC."""
    zone = ZoneInfo(zone_name or "UTC")

    def local(moment: datetime | None, *, with_time: bool = True) -> str:
        """A stored instant as a date in the display zone, for a page."""
        if moment is None:
            return "—"
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")

    return {"number": format_number, "local": local}


def utc_now() -> datetime:
    return datetime.now(UTC)
