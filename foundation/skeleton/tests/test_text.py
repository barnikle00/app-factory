from datetime import UTC, datetime

from app.core.text import format_number, normalize_digits, template_filters


def test_digits_of_any_script_become_ascii_and_input_is_trimmed():
    assert normalize_digits(" ۱۲۳٤٥ ") == "12345"  # Persian and Arabic-Indic
    assert normalize_digits("१२३") == "123"  # Devanagari
    assert normalize_digits("v2") == "v2"


def test_numbers_are_grouped_by_thousands():
    assert format_number(1234567) == "1,234,567"
    assert format_number("v2") == "v2"


def test_a_stored_utc_instant_is_shown_in_the_display_zone():
    moment = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
    assert template_filters("")["local"](moment) == "2026-09-30 10:00"
    assert template_filters("Europe/Berlin")["local"](moment) == "2026-09-30 12:00"
    assert template_filters("")["local"](None) == "—"
