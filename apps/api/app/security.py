"""Password verification, session tokens, CSRF, and login rate limiting.

Rate limiting is intentionally in-memory and per-process in slice 1.
It is documented as temporary in ARCHITECTURE.md: with more than one API
worker it will not be shared, and a later phase must move it to the
database (or Redis) before scaling beyond one replica.
"""

import hashlib
import secrets
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from . import config

_ph = PasswordHasher()


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_hex(32)


def verify_app_password(password: str) -> bool:
    """Verify against the Argon2 hash from the environment.

    Returns False (not an exception) when no hash is configured, so the
    caller can return a clean 503 instead of leaking configuration state.
    """
    if not config.APP_PASSWORD_HASH:
        return False
    try:
        return _ph.verify(config.APP_PASSWORD_HASH, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# --- CSRF -----------------------------------------------------------------
# One random CSRF token per session, stored in the sessions table. The
# client reads it from GET /api/auth/csrf (authenticated) and sends it back
# as X-CSRF-Token on mutations (logout today, all mutations later).


def new_csrf_token() -> str:
    return secrets.token_hex(32)


# --- Login rate limiting (in-memory, per-process, temporary) -------------
_attempts: dict[str, deque] = defaultdict(deque)


def login_allowed(client_ip: str) -> bool:
    now = time.monotonic()
    window = _attempts[client_ip]
    while window and now - window[0] > config.LOGIN_RATE_WINDOW_SECONDS:
        window.popleft()
    return len(window) < config.LOGIN_RATE_LIMIT


def record_login_attempt(client_ip: str) -> None:
    _attempts[client_ip].append(time.monotonic())


def reset_rate_limits() -> None:
    """Test helper only. Never expose this over HTTP."""
    _attempts.clear()
