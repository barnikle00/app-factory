from datetime import UTC, datetime

from app.auth import session as tickets
from app.auth.passwords import ALPHABET, hash_password, new_initial_password, password_matches
from tests.conftest import make_settings

AUTH = make_settings().auth
CHANGED = datetime(2026, 9, 30, tzinfo=UTC)


def test_a_password_is_stored_as_a_hash_and_checked():
    stored = hash_password(AUTH, "MKPR-XQTD")
    assert "MKPR" not in stored
    assert password_matches(AUTH, stored, "MKPR-XQTD")
    assert not password_matches(AUTH, stored, "wrong")
    assert not password_matches(AUTH, "", "anything")  # a damaged hash refuses, never crashes


def test_the_initial_password_has_no_digit_and_no_I_or_O():
    pw = new_initial_password(AUTH)
    assert set(pw.replace("-", "")) <= set(ALPHABET) and len(pw.replace("-", "")) == 16


def test_a_session_ticket_round_trips_and_a_forged_one_is_refused():
    token = tickets.issue(AUTH, colleague_id=7, password_changed_at=CHANGED)
    assert tickets.read(AUTH, token) == tickets.Ticket(7, tickets.stamp(CHANGED))
    assert tickets.read(AUTH, token[:-2] + "xx") is None
    assert tickets.read(AUTH, None) is None


def test_a_session_older_than_the_idle_timeout_is_refused(monkeypatch):
    token = tickets.issue(AUTH, colleague_id=7, password_changed_at=CHANGED)
    import itsdangerous.timed as timed

    later = timed.time.time() + AUTH.session_idle_timeout_hours * 3600 + 5
    monkeypatch.setattr(timed.time, "time", lambda: later)
    assert tickets.read(AUTH, token) is None
