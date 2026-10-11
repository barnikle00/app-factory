"""Persian at the edges: digits in (ADR 0006), digits and dates out (ADR 0003).

Stored instants are UTC; Tehran and the Jalali calendar are how a person reads them, applied only
when a page is drawn. This file replaces the neutral `app/core/text.py` and keeps its public
names (`normalize_digits`, `utc_now`, `template_filters`), so nothing else in the app changes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import jdatetime

DEFAULT_ZONE = "Asia/Tehran"
DS_OPTIONS = {"lang": "fa", "direction": "rtl", "calendar": "jalali"}
_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def normalize_digits(value: str) -> str:
    """Persian and Arabic-Indic digits to ASCII, and ي/ك to ی/ک — once, where input arrives."""
    return value.translate(_TO_ASCII).replace("ي", "ی").replace("ك", "ک").strip()


def fa_digits(value: object) -> str:
    """ASCII digits to Persian, for display. Thousands are grouped with «٬»."""
    text = f"{value:,}".replace(",", "٬") if isinstance(value, int) else str(value)
    return text.translate(_TO_PERSIAN)


def local_jalali(
    moment: datetime | None, *, with_time: bool = True, zone: ZoneInfo | None = None
) -> str:
    """A stored UTC instant as a Jalali date for a page — «۱۴۰۵/۰۷/۰۸ ۱۴:۳۰»."""
    if moment is None:
        return "—"
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    local = jdatetime.datetime.fromgregorian(
        datetime=moment.astimezone(zone or ZoneInfo(DEFAULT_ZONE))
    )
    return fa_digits(local.strftime("%Y/%m/%d %H:%M" if with_time else "%Y/%m/%d"))


def template_filters(zone_name: str) -> dict[str, Callable[..., str]]:
    """The two filters every template uses: `number` and `local`. An empty zone means Tehran."""
    zone = ZoneInfo(zone_name or DEFAULT_ZONE)

    def local(moment: datetime | None, *, with_time: bool = True) -> str:
        return local_jalali(moment, with_time=with_time, zone=zone)

    return {"number": fa_digits, "local": local}


def utc_now() -> datetime:
    return datetime.now(UTC)
