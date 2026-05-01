"""
TOTP-based Multi-Factor Authentication using pyotp.
Supports Google Authenticator, Authy, and any TOTP app.
Includes backup code generation and management.
"""

import base64
import io

import pyotp
import qrcode
import structlog

from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

ISSUER_NAME = "SintraPrime Portal"
TOTP_DIGITS = 6
TOTP_INTERVAL = 30
TOTP_VALID_WINDOW = 1  # allow ±1 interval for clock drift


class MFAError(Exception):
    """Raised on MFA validation failure."""
    pass


def generate_totp_secret() -> str:
    """Generate a new base32-encoded TOTP secret."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, tenant_name: str = "SintraPrime") -> str:
    """Build an otpauth:// URI for QR code generation."""
    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL,
        issuer=f"{ISSUER_NAME} ({tenant_name})",
    )
    return totp.provisioning_uri(name=email, issuer_name=f"{ISSUER_NAME} ({tenant_name})")


def generate_qr_code_base64(totp_uri: str) -> str:
    """
    Generate a QR code image as a base64-encoded PNG string.
    Returns: data URL string suitable for <img src="...">
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4,
    )
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a TOTP code against the secret.
    Returns True if valid within the allowed window.
    """
    if not secret or not code:
        return False
    totp = pyotp.TOTP(
        secret,
        digits=TOTP_DIGITS,
        interval=TOTP_INTERVAL,
    )
    return totp.verify(code.replace(" ", ""), valid_window=TOTP_VALID_WINDOW)


def get_current_totp(secret: str) -> str:
    """Get the current TOTP value (for testing/debugging only)."""
    return pyotp.TOTP(secret).now()


class TOTPSetup:
    """Helper object returned during MFA setup flow."""

    def __init__(self, email: str, tenant_name: str = "SintraPrime"):
        self.secret = generate_totp_secret()
        self.uri = get_totp_uri(self.secret, email, tenant_name)
        self.qr_code = generate_qr_code_base64(self.uri)

    def verify(self, code: str) -> bool:
        return verify_totp(self.secret, code)

    def to_dict(self) -> dict:
        return {
            "secret": self.secret,
            "uri": self.uri,
            "qr_code": self.qr_code,
        }
