"""How a password is stored (argon2, cost from settings) and the initial one the owner reads out.

The initial password is letters only, without I and O: it is read off a screen and spoken across a
desk, so it must not hold characters that look alike or that a page in another script would render
differently.
"""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import AuthSettings

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"
GROUP_SIZE = 4


def _hasher(auth: AuthSettings) -> PasswordHasher:
    return PasswordHasher(
        time_cost=auth.password_hash_time_cost_count,
        memory_cost=auth.password_hash_memory_cost_kib,
        parallelism=auth.password_hash_parallelism_count,
    )


def hash_password(auth: AuthSettings, password: str) -> str:
    return _hasher(auth).hash(password)


def password_matches(auth: AuthSettings, stored_hash: str, password: str) -> bool:
    """A damaged or empty stored hash refuses every password rather than crashing the page."""
    try:
        return _hasher(auth).verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def new_initial_password(auth: AuthSettings) -> str:
    """«MKPR-XQTD-HJBW-NFVS» — shown once; only its hash is kept."""
    letters = "".join(secrets.choice(ALPHABET) for _ in range(auth.initial_password_length_chars))
    return "-".join(letters[i : i + GROUP_SIZE] for i in range(0, len(letters), GROUP_SIZE))
