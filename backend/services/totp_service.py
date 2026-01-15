"""TOTP authentication service."""

import hashlib
import hmac
import secrets
import time
from functools import lru_cache

import pyotp

from settings.config import get_settings


class TOTPService:
    """Service for TOTP authentication and session management."""

    def __init__(self) -> None:
        """Initialize TOTP service with settings."""
        self.settings = get_settings()
        self._totp = None
        self._sessions: dict[str, float] = {}  # token -> expiry timestamp
        self._session_duration = 3600  # 1 hour in seconds

    @property
    def totp(self) -> pyotp.TOTP:
        """Get or create TOTP instance."""
        if self._totp is None:
            if not self.settings.totp_secret:
                raise ValueError("TOTP_SECRET not configured in environment")
            self._totp = pyotp.TOTP(self.settings.totp_secret)
        return self._totp

    @property
    def enabled(self) -> bool:
        """Check if TOTP authentication is enabled."""
        return self.settings.totp_enabled and bool(self.settings.totp_secret)

    def verify_code(self, code: str) -> bool:
        """
        Verify a TOTP code.

        Args:
            code: The 6-digit TOTP code to verify

        Returns:
            True if the code is valid, False otherwise
        """
        if not self.enabled:
            return True  # If TOTP is disabled, always allow access

        try:
            return self.totp.verify(code, valid_window=self.settings.totp_valid_window)
        except Exception:
            return False

    def generate_session_token(self) -> str:
        """
        Generate a secure session token.

        Returns:
            A secure random token string
        """
        token = secrets.token_urlsafe(32)
        expiry = time.time() + self._session_duration
        self._sessions[token] = expiry
        return token

    def validate_session_token(self, token: str) -> bool:
        """
        Validate a session token.

        Args:
            token: The session token to validate

        Returns:
            True if the token is valid and not expired
        """
        if not self.enabled:
            return True  # If TOTP is disabled, always allow access

        if token not in self._sessions:
            return False

        expiry = self._sessions[token]
        if time.time() > expiry:
            # Token expired, remove it
            del self._sessions[token]
            return False

        return True

    def invalidate_session(self, token: str) -> None:
        """
        Invalidate a session token.

        Args:
            token: The session token to invalidate
        """
        self._sessions.pop(token, None)

    def get_provisioning_uri(self, name: str = "Sherlock") -> str:
        """
        Get the provisioning URI for adding to authenticator app.

        Args:
            name: The name to display in the authenticator app

        Returns:
            The otpauth:// URI for QR code generation
        """
        return self.totp.provisioning_uri(name=name, issuer_name="Sherlock")

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from memory.

        Returns:
            Number of sessions removed
        """
        current_time = time.time()
        expired = [token for token, expiry in self._sessions.items() if current_time > expiry]
        for token in expired:
            del self._sessions[token]
        return len(expired)


@lru_cache
def get_totp_service() -> TOTPService:
    """Get cached TOTP service instance."""
    return TOTPService()
