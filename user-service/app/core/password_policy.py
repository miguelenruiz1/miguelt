"""Password policy enforcement.

Rules (FASE4):
- Min 12 chars
- At least 1 uppercase, 1 lowercase, 1 digit, 1 symbol
- Reject common weak passwords (hardcoded top-100 list)

Raises ValidationError on failure.
"""
from __future__ import annotations

import re

from app.core.errors import ValidationError


MIN_LENGTH = 12

# Top-100 most common passwords (hardcoded — no external dep).
# Lowercased for case-insensitive match.
_COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345",
    "1234", "111111", "1234567", "dragon", "123123", "baseball", "abc123",
    "football", "monkey", "letmein", "696969", "shadow", "master", "666666",
    "qwertyuiop", "123321", "mustang", "1234567890", "michael", "654321",
    "pussy", "superman", "1qaz2wsx", "7777777", "fuckyou", "121212", "000000",
    "qazwsx", "123qwe", "killer", "trustno1", "jordan", "jennifer", "zxcvbnm",
    "asdfgh", "hunter", "buster", "soccer", "harley", "batman", "andrew",
    "tigger", "sunshine", "iloveyou", "fuckme", "2000", "charlie", "robert",
    "thomas", "hockey", "ranger", "daniel", "starwars", "klaster", "112233",
    "george", "asshole", "computer", "michelle", "jessica", "pepper", "1111",
    "zxcvbn", "555555", "11111111", "131313", "freedom", "777777", "pass",
    "fuck", "maggie", "159753", "aaaaaa", "ginger", "princess", "joshua",
    "cheese", "amanda", "summer", "love", "ashley", "6969", "nicole",
    "chelsea", "biteme", "matthew", "access", "yankees", "987654321", "dallas",
    "austin", "thunder", "taylor", "matrix",
    # Sadly common in Colombia/LatAm
    "colombia", "bogota", "medellin", "cali", "trace",
}


def validate_password(password: str) -> None:
    """Raise ValidationError if password doesn't meet policy."""
    if not password or len(password) < MIN_LENGTH:
        raise ValidationError(
            f"La contraseña debe tener al menos {MIN_LENGTH} caracteres."
        )

    if not re.search(r"[A-Z]", password):
        raise ValidationError("La contraseña debe incluir al menos una mayúscula.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("La contraseña debe incluir al menos una minúscula.")
    if not re.search(r"\d", password):
        raise ValidationError("La contraseña debe incluir al menos un número.")
    if not re.search(r"[^A-Za-z0-9]", password):
        raise ValidationError("La contraseña debe incluir al menos un símbolo.")

    if password.lower() in _COMMON_PASSWORDS:
        raise ValidationError(
            "Esa contraseña aparece en listas de contraseñas comunes. Escoge una diferente."
        )
