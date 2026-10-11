"""ds — the design system's Jinja integration.

    from ds import install
    env = install(Environment(loader=...), brand="slate", app_name="…", dev=True)

Provides the three globals and two filters the macros call, and nothing else.
No dependency beyond Jinja2: the optional Jalali calendar is ~20 lines of arithmetic and
carrying a package for it would make the design system unusable in the one place
it most needs to work — a fresh project on day one.

Native-script digits (Persian, Arabic-Indic…) are deliberately NOT the default. Tabular Latin
figures in an isolated left-to-right island are what make a column of money legible and
copy-pasteable; native digits look right and break both. `ds_money(fa=True)` exists for prose in
Persian, where it is correct. Dates are Gregorian unless `install(calendar="jalali")` says otherwise.
"""

from __future__ import annotations

import datetime as _dt
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                       # pragma: no cover
    from jinja2 import Environment

__all__ = ["DesignSystemError", "install", "to_jalali"]


class DesignSystemError(Exception):
    """A macro was called in a way the contract forbids."""


# ── Jalali ───────────────────────────────────────────────────────────────────
# The standard algorithm. Correct for 1900-2100, which is the whole range any of
# these applications will see.

_G_DAYS = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def to_jalali(d: _dt.date) -> tuple[int, int, int]:
    gy, gm, gd = d.year, d.month, d.day
    gy2 = gy - 1 if gm <= 2 else gy
    days = (355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 + gd + _G_DAYS[gm - 1])
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(s: str) -> str:
    return s.translate(_FA_DIGITS)


def normalize_digits(s: str) -> str:
    """Persian and Arabic-Indic digits → ASCII. Needed on every form field that
    takes a number, because a phone keyboard set to such a script produces ۱۲۳ and
    int('۱۲۳') raises. Re-implemented independently in four projects before the factory."""
    return s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


# ── Filters ──────────────────────────────────────────────────────────────────

def ds_money(value: Any, fa: bool = False) -> str:
    """Group by thousands. One place, so no template invents its own separator."""
    if value is None or value == "":
        return "—"
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return str(value)
    s = f"{abs(n):,}".replace(",", "٬" if fa else ",")
    if n < 0:
        s = "-" + s
    return _fa(s) if fa else s


def ds_date(value: Any, with_time: bool = False, fa: bool = False,
            calendar: str = "gregorian") -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, str):
        return value
    d = value.date() if isinstance(value, _dt.datetime) else value
    y, m, day = to_jalali(d) if calendar == "jalali" else (d.year, d.month, d.day)
    s = f"{y:04d}/{m:02d}/{day:02d}"
    if with_time and isinstance(value, _dt.datetime):
        s += f" {value.hour:02d}:{value.minute:02d}"
    return _fa(s) if fa else s


# ── Interface strings ────────────────────────────────────────────────────────
# The few words a macro prints on its own (a default, an aria-label). Everything else a page says is
# passed in by the screen. `install(strings={...})` overrides any of them, or adds a language.

UI_STRINGS: dict[str, dict[str, str]] = {
    "en": {"nothing_here": "Nothing here", "previous": "Previous", "next": "Next",
           "close": "Close", "pagination": "Pagination", "breadcrumb": "Breadcrumb"},
    "fa": {"nothing_here": "چیزی اینجا نیست", "previous": "قبلی", "next": "بعدی",
           "close": "بستن", "pagination": "صفحه‌بندی", "breadcrumb": "مسیر"},
}


# ── The failure global ───────────────────────────────────────────────────────

def _make_fail(dev: bool):
    """button(intent="blue") must not render quietly.

    In dev it raises, so the wrong call is found by the person who wrote it. In
    production it renders a visible marker instead of taking the page down — a
    design-system misuse on one screen is not worth a 500 on a live dashboard,
    and an invisible failure is how the system's rules stop being real."""

    from markupsafe import Markup, escape

    def ds_fail(message: str) -> Markup:
        if dev:
            raise DesignSystemError(message)
        return Markup('<span class="pill pill-danger" role="alert">'
                      f"ds: {escape(message)}</span>")

    return ds_fail


# ── Install ──────────────────────────────────────────────────────────────────

def install(env: Environment, *, brand: str, app_name: str,
            static_url: str = "/static/ds/", dev: bool = False,
            lang: str = "en", direction: str = "ltr",
            calendar: str = "gregorian",
            strings: dict[str, str] | None = None) -> Environment:
    """Register everything base.html and ds.html expect. Call once at startup.

    `lang` and `direction` describe the app's language ("fa" / "rtl" for Persian); `calendar`
    is "gregorian" or "jalali" and decides what the `datestamp` macro prints."""
    env.filters["ds_money"] = ds_money
    env.filters["ds_date"] = (
        lambda value, with_time=False, fa=False: ds_date(value, with_time, fa, calendar))
    words = {**UI_STRINGS["en"], **UI_STRINGS.get(lang, {}), **(strings or {})}
    globals_: dict[str, Any] = {
        "ds_t": lambda key: words[key],
        "ds_fail": _make_fail(dev),
        "ds_static": lambda name: f"{static_url.rstrip('/')}/{name}",
        "ds_brand": brand,
        "ds_app_name": app_name,
        "ds_lang": lang,
        "ds_dir": direction,
        "ds_flash": [],
        "ds_dev": dev,
    }
    env.globals.update(globals_)
    # StrictUndefined in dev only. A typo'd variable in a template renders as an
    # empty string by default, which is the same silent-blank failure the brand
    # check exists to stop — but turning it on in production converts a typo in a
    # rarely-visited branch into a 500 on a live page.
    if dev:
        from jinja2 import StrictUndefined
        env.undefined = StrictUndefined
    return env
