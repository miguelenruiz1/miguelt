"""QR code generation for certificate verification URLs."""
from __future__ import annotations

import base64
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_H


def generate_qr(url: str) -> bytes:
    """Generate a QR code PNG for the given URL.

    Returns the raw PNG bytes.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_qr_base64(url: str) -> str:
    """Generate a QR code as a base64 data URI for embedding in HTML."""
    png_bytes = generate_qr(url)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"
