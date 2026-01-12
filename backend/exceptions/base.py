"""Base exception classes for the application."""


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 400,
        details: dict | None = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            code: Machine-readable error code (e.g., "VALIDATION_ERROR")
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }
