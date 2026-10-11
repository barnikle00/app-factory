"""The design system's own tests.

These check the STRUCTURAL guarantees — the ones the macros exist to make
unrepresentable. A test that only asserted "the macro renders" would pass just as
happily on a component set that lets you put three primary buttons in a row.

Run:  python3 -m pytest tests/ -q
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

DESIGN = Path(__file__).resolve().parent.parent / "foundation" / "design"
sys.path.insert(0, str(DESIGN))
import ds  # noqa: E402


def env(dev: bool = True, **install_kw) -> Environment:
    """A right-to-left Persian app on the Jalali calendar — the hardest case, so the one tested.
    The defaults (English, left-to-right, Gregorian) are pinned separately below."""
    e = Environment(loader=FileSystemLoader(str(DESIGN / "templates")),
                    autoescape=True, trim_blocks=True, lstrip_blocks=True)
    kw = {"lang": "fa", "direction": "rtl", "calendar": "jalali", **install_kw}
    return ds.install(e, brand="slate", app_name="آزمون", dev=dev, **kw)


def render(source: str, dev: bool = True, **ctx) -> str:
    return env(dev).from_string(
        '{% import "ds.html" as ds %}' + source).render(**ctx)


# ── The guarantees ───────────────────────────────────────────────────────────

def test_actions_can_emit_at_most_one_primary():
    """The signature has one primary slot, so this is structural, not reviewed."""
    out = render('{{ ds.actions(primary={"label": "ذخیره"}, '
                 'secondary=[{"label": "انصراف"}, {"label": "پیش‌نویس"}]) }}')
    assert out.count("btn-primary") == 1
    assert out.count("btn-secondary") == 2


def test_table_always_writes_its_own_scroll_container():
    """Without it a phone scrolls the page body sideways — the most common
    failure mode of an RTL dashboard, and one no reviewer catches on a laptop."""
    out = render('{{ ds.table(cols, rows) }}',
                 cols=[{"key": "a", "label": "الف"}], rows=[{"a": 1}])
    assert '<div class="table-scroll">' in out
    assert out.index("table-scroll") < out.index("<table")


def test_table_with_no_rows_renders_an_empty_state_not_an_empty_table():
    out = render('{{ ds.table(cols, [], empty_title="هیچ تراکنشی نیست") }}',
                 cols=[{"key": "a", "label": "الف"}])
    assert "هیچ تراکنشی نیست" in out
    assert "<table" not in out


def test_a_bad_intent_fails_loudly_in_dev():
    with pytest.raises(ds.DesignSystemError):
        render('{{ ds.button("خطا", intent="blue") }}')
    with pytest.raises(ds.DesignSystemError):
        render('{{ ds.pill("خطا", intent="purple") }}')


def test_a_bad_intent_is_visible_but_not_fatal_in_production():
    """A misuse on one screen must not take a live dashboard down — and must not
    be invisible either, or the closed set stops being real."""
    out = render('{{ ds.button("خطا", intent="blue") }}', dev=False)
    assert "pill-danger" in out and "ds:" in out


def test_every_interactive_element_carries_data_tap():
    """The 44px floor selects on this attribute, so a new macro that forgets it
    silently opts out of the touch target rule."""
    for source in ('{{ ds.button("د") }}',
                   '{{ ds.field("n", "برچسب") }}',
                   '{{ ds.select("n", "برچسب", ["الف"]) }}',
                   '{{ ds.tabs([{"key": "a", "href": "/a", "label": "الف"}], "a") }}'):
        out = render(source)
        assert "data-tap" in out, source


def test_select_writes_its_own_wrapper():
    """A <select> cannot carry a pseudo-element, and background-position has no
    logical form — so the chevron has to come from a wrapper the macro emits."""
    out = render('{{ ds.select("n", "برچسب", ["الف", "ب"]) }}')
    assert 'class="select-wrap' in out
    assert out.index("select-wrap") < out.index("<select")


def test_no_macro_emits_an_inline_style():
    """The template linter rejects `style=` outright. That rule only survives if
    the system's own components never need the exception."""
    out = render(
        '{{ ds.field("n", "ب", width="amount") }}'
        '{{ ds.select("n", "ب", ["الف"], width="date") }}'
        '{{ ds.table([{"key": "a", "label": "الف", "width": "amount", "num": true}],'
        '            [{"a": 1}]) }}')
    assert "style=" not in out
    assert "w-amount" in out and "w-date" in out


def test_no_macro_emits_a_colour():
    """Every colour in the system comes from the brand file. A hex in rendered
    HTML is a colour that cannot follow the brand."""
    out = render('{{ ds.pill("فعال", intent="ok") }}{{ ds.alert("هشدار") }}'
                 '{{ ds.stat("جمع", "۱۲") }}{{ ds.empty("خالی") }}')
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", out)


def test_amount_isolates_direction_so_digits_cannot_reorder():
    out = render("{{ ds.amount(-1234567, unit='ریال') }}")
    assert 'class="amount amount-neg"' in out
    assert "1,234,567" in out


def test_datestamp_renders_jalali():
    out = render("{{ ds.datestamp(d) }}", d=dt.date(2026, 9, 12))
    assert "1405/06/21" in out


def test_the_defaults_are_english_left_to_right_and_gregorian():
    plain = ds.install(Environment(loader=FileSystemLoader(str(DESIGN / "templates")),
                                   autoescape=True), brand="slate", app_name="App", dev=True)
    page = plain.get_template("base.html").render()
    assert 'dir="ltr"' in page and 'lang="en"' in page
    out = plain.from_string('{% import "ds.html" as ds %}{{ ds.datestamp(d) }}').render(
        d=dt.date(2026, 9, 12))
    assert "2026/09/12" in out


def test_a_column_that_is_both_num_and_nowrap_emits_one_class_attribute():
    """Two class attributes on one element means the second is silently dropped."""
    out = render('{{ ds.table(cols, rows) }}',
                 cols=[{"key": "a", "label": "الف", "num": True, "nowrap": True}],
                 rows=[{"a": 1}])
    cell = re.search(r"<td[^>]*>", out).group(0)
    assert cell.count("class=") == 1
    assert "num" in cell and "nowrap" in cell


def test_the_macro_set_is_exactly_seventeen_and_the_file_parses():
    """Two things at once, and neither is "they render" — the tests above do that.
    Parsing ds.html is what fails when a macro is edited into a syntax error while
    no screen calls it yet; the count is what fails when someone adds an
    eighteenth instead of arguing for it."""
    e = env()
    mod = e.get_template("ds.html").module
    names = [n for n in dir(mod) if not n.startswith("_")]
    assert len(names) == 17, names


def test_base_loads_the_brand_before_core():
    """The other order arrives after the rules that read the values, and every
    var() in core.css falls back to nothing. It renders as an unstyled page,
    which reads like a broken build rather than a stylesheet ordering bug."""
    out = env().get_template("base.html").render()
    assert out.index("brand-slate.css") < out.index("core.css")
    assert 'dir="rtl"' in out and 'lang="fa"' in out
    assert "user-scalable=no" not in out and "maximum-scale" not in out


# ── The helpers ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("g,j", [
    ((2026, 9, 12), "1405/06/21"),
    ((2026, 3, 21), "1405/01/01"),   # Nowruz
    ((2026, 3, 20), "1404/12/29"),   # the day before
    ((2025, 3, 20), "1403/12/30"),   # a leap year's 30th of Esfand
    ((2026, 1, 1), "1404/10/11"),
])
def test_jalali(g, j):
    assert ds.ds_date(dt.date(*g), calendar="jalali") == j


def test_money_uses_latin_tabular_digits_by_default():
    """Persian digits look right in a column of money and break both legibility
    and copy-paste. They stay available for prose, where they are correct."""
    assert ds.ds_money(1234567) == "1,234,567"
    assert ds.ds_money(1234567, fa=True) == "۱٬۲۳۴٬۵۶۷"
    assert ds.ds_money(None) == "—"
    assert ds.ds_money("not a number") == "not a number"


def test_digit_normalisation_covers_arabic_indic_too():
    """A phone keyboard set to Persian produces ۱۲۳; one set to Arabic produces
    ١٢٣. int() raises on both, and four projects have re-solved this."""
    assert ds.normalize_digits("۱۲۳") == "123"
    assert ds.normalize_digits("١٢٣") == "123"
