"""Runtime configuration for the Harlearn API (slice 1).

All secrets come from the environment. Nothing here has a default secret.
``HARLEARN_APP_PASSWORD_HASH`` must be an Argon2 hash produced by
``tools/hash_password.py`` -- never a plaintext password.
"""

import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://harlearn:harlearn@db:5432/harlearn"
)
# SQLite is only a test/dev fallback; production (compose) uses PostgreSQL.
APP_PASSWORD_HASH = os.environ.get("HARLEARN_APP_PASSWORD_HASH", "")
WEB_ORIGIN = os.environ.get("WEB_ORIGIN", "http://127.0.0.1:3000")
COOKIE_NAME = "harlearn_session"
# Fernet key for provider API keys (phase 2). There is deliberately NO
# default and NO auto-generation: a generated-on-startup key would make
# every stored connection undecryptable after a restart. Deploy must set
# HARLEARN_FERNET_KEY (generate with: python -c "from cryptography.fernet
# import Fernet; print(Fernet.generate_key().decode())"). In .env for
# Docker Compose it is a plain value with no '$', so no $$-escaping issue.
FERNET_KEY = os.environ.get("HARLEARN_FERNET_KEY", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
SESSION_TTL_DAYS = 7
LOGIN_RATE_LIMIT = 5  # attempts
LOGIN_RATE_WINDOW_SECONDS = 15 * 60
