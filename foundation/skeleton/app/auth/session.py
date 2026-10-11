"""The signed session cookie — no session table, so a restarted `web` process signs nobody out.

It expires after `session_idle_timeout_hours` without a request (it is re-issued on every page), and
it carries the moment the password last changed, so a password change ends every other session.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import SECONDS_PER_HOUR, AuthSettings

SALT = "factory-app.session"
VERSION = 1
MICROSECONDS = 1_000_000


@dataclass(frozen=True)
class Ticket:
    colleague_id: int
    password_stamp: int


def _serializer(auth: AuthSettings) -> URLSafeTimedSerializer:
    if not auth.session_signing_key:
        raise RuntimeError(
            "AUTH_SESSION_SIGNING_KEY is empty — set it in the environment of `web`."
        )
    return URLSafeTimedSerializer(auth.session_signing_key, salt=SALT)


def stamp(moment: datetime) -> int:
    return int(moment.timestamp() * MICROSECONDS)


def issue(auth: AuthSettings, *, colleague_id: int, password_changed_at: datetime) -> str:
    return _serializer(auth).dumps(
        {"v": VERSION, "id": colleague_id, "pw": stamp(password_changed_at)}
    )


def read(auth: AuthSettings, token: str | None) -> Ticket | None:
    """The ticket, or None for absent, expired or forged — one answer, so a forger learns nothing."""
    if not token:
        return None
    try:
        payload = _serializer(auth).loads(
            token, max_age=auth.session_idle_timeout_hours * SECONDS_PER_HOUR
        )
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict) or payload.get("v") != VERSION:
        return None
    cid, pw = payload.get("id"), payload.get("pw")
    if not isinstance(cid, int) or not isinstance(pw, int):
        return None
    return Ticket(cid, pw)
