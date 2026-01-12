"""LLM-specific exceptions."""

from exceptions.base import AppException


class LLMException(AppException):
    """Base exception for LLM errors."""

    def __init__(
        self, message: str, code: str = "LLM_ERROR", details: dict | None = None
    ):
        super().__init__(message=message, code=code, status_code=500, details=details)


class LLMConnectionError(LLMException):
    """Failed to connect to LLM provider."""

    def __init__(self, provider: str, reason: str = ""):
        details = {"provider": provider, "reason": reason}
        super().__init__(
            message=f"Failed to connect to {provider}: {reason}",
            code="LLM_CONNECTION_ERROR",
            details=details,
        )


class LLMRateLimitError(LLMException):
    """LLM rate limit exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        details = {"provider": provider, "retry_after": retry_after}
        super().__init__(
            message=f"Rate limit exceeded for {provider}",
            code="LLM_RATE_LIMIT",
            details=details,
        )


class LLMResponseError(LLMException):
    """Invalid or unexpected response from LLM."""

    def __init__(self, provider: str, reason: str = ""):
        details = {"provider": provider, "reason": reason}
        super().__init__(
            message=f"Invalid response from {provider}: {reason}",
            code="LLM_RESPONSE_ERROR",
            details=details,
        )


class LLMConfigurationError(LLMException):
    """LLM configuration error."""

    def __init__(self, llm_id: str, reason: str = ""):
        details = {"llm_id": llm_id, "reason": reason}
        super().__init__(
            message=f"Configuration error for {llm_id}: {reason}",
            code="LLM_CONFIG_ERROR",
            details=details,
        )
