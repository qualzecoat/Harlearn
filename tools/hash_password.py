#!/usr/bin/env python3
"""Generate an Argon2 hash for the Harlearn single app password.

Usage (from the repo root, with the API venv active or argon2 installed):
    python tools/hash_password.py

The password is read via getpass (never from argv, never printed, never
saved by this script). Paste the printed hash into HARLEARN_APP_PASSWORD_HASH
in your .env file. The .env file itself must never be committed.
"""

import getpass
import sys

try:
    from argon2 import PasswordHasher
except ImportError:
    print("argon2-cffi is required: pip install -r apps/api/requirements.txt", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    password = getpass.getpass("Harlearn app password: ")
    confirm = getpass.getpass("Repeat app password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        raise SystemExit(1)
    if not password:
        print("Password must not be empty.", file=sys.stderr)
        raise SystemExit(1)
    print(PasswordHasher().hash(password))


if __name__ == "__main__":
    main()
