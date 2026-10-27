"""Provider API-key encryption (phase 2).

Keys are encrypted with Fernet (AES-128-CBC + HMAC) using
HARLEARN_FERNET_KEY from the environment. The encrypted value is what
is stored in the database; the plaintext key is never stored, never
logged, and never returned by any endpoint. If no Fernet key is
configured, encryption/decryption fail loudly (503 at the API layer)
instead of silently storing plaintext.
"""

from cryptography.fernet import Fernet, InvalidToken

from . import config


def _fernet() -> Fernet:
    if not config.FERNET_KEY:
        raise ValueError("FERNET_KEY not configured")
    return Fernet(config.FERNET_KEY.encode("utf-8"))


def encrypt_api_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("cannot decrypt stored API key (wrong FERNET_KEY?)") from exc


def mask_api_key(plaintext: str) -> str:
    """Masked display only, e.g. 'sk-...abcd' or '••••' for short keys.

    The masked form is derived from the plaintext at read time; the
    plaintext itself is never sent to the client.
    """
    if len(plaintext) <= 4:
        return "••••"
    return plaintext[:3] + "…" + plaintext[-4:]
