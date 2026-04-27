"""At-rest encryption for sensitive fields (wallet secret keys, etc.)

Uses Fernet (AES-128-CBC + HMAC-SHA256) with a key from settings.FERNET_KEY.
In dev (no key set) it returns the value as-is so local development isn't
blocked, but the boot validator (settings.validate_fernet_key) refuses prod
without a real key.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.settings import get_settings


def _get_fernet() -> Fernet | None:
    settings = get_settings()
    key = (settings.FERNET_KEY or "").strip()
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            pass
    # Dev fallback: derive from JWT_SECRET so local development works
    # without an explicit FERNET_KEY. Production validator forbids this path.
    secret = settings.JWT_SECRET.encode()
    derived = hashlib.sha256(secret).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a sensitive string for at-rest storage. Returns the ciphertext as a string."""
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a previously encrypted secret.

    - Si parece Fernet (empieza con `gAAAAA`) y no se decifra → lanza ValueError.
      Eso EVITA devolver el ciphertext crudo como si fuera plaintext (bug donde
      el worker recibía `gAAAAAB...` y lo intentaba parsear como base58).
    - Si NO parece Fernet → asume legacy plaintext (registros viejos pre-encryption)
      y lo devuelve tal cual.
    """
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        if ciphertext.startswith("gAAAAA"):
            raise ValueError(
                "Fernet ciphertext no decifrable — posible mismatch entre "
                "FERNET_KEY/JWT_SECRET de los servicios. Verifica que api y worker "
                "compartan el mismo secret en docker-compose."
            )
        # Pre-encryption legacy plaintext: devolver tal cual.
        return ciphertext
