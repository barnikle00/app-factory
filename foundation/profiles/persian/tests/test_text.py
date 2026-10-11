from datetime import UTC, datetime

from app.core.text import fa_digits, local_jalali, normalize_digits, template_filters


def test_persian_and_arabic_input_becomes_one_spelling():
    assert normalize_digits(" ۱۲۳٤٥ ") == "12345"
    assert normalize_digits("علي كريمي") == "علی کریمی"


def test_numbers_are_shown_in_persian_digits_grouped():
    assert fa_digits(1234567) == "۱٬۲۳۴٬۵۶۷"
    assert fa_digits("v2") == "v۲"


def test_a_stored_utc_instant_is_shown_as_a_jalali_date():
    # 2026-09-30 10:00 UTC is 13:30 in Tehran, 8 Mehr 1405.
    assert local_jalali(datetime(2026, 9, 30, 10, 0, tzinfo=UTC)) == "۱۴۰۵/۰۷/۰۸ ۱۳:۳۰"
    assert local_jalali(None) == "—"


def test_the_template_filters_default_to_tehran_and_obey_the_setting():
    moment = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
    assert template_filters("")["local"](moment) == "۱۴۰۵/۰۷/۰۸ ۱۳:۳۰"
    assert template_filters("UTC")["local"](moment) == "۱۴۰۵/۰۷/۰۸ ۱۰:۰۰"
    assert template_filters("")["number"](1234567) == "۱٬۲۳۴٬۵۶۷"
