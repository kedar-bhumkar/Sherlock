"""Ingestion-specific exceptions."""

from exceptions.base import AppException


class IngestionException(AppException):
    """Base exception for ingestion errors."""

    def __init__(self, message: str, code: str = "INGESTION_ERROR", details: dict | None = None):
        super().__init__(message=message, code=code, status_code=400, details=details)


class ImageDownloadError(IngestionException):
    """Failed to download or access image."""

    def __init__(self, url: str, reason: str = ""):
        details = {"url": url, "reason": reason}
        super().__init__(
            message=f"Failed to download image: {reason}",
            code="IMAGE_DOWNLOAD_ERROR",
            details=details,
        )


class InvalidImageError(IngestionException):
    """Image format is invalid or unsupported."""

    def __init__(self, url: str, reason: str = ""):
        details = {"url": url, "reason": reason}
        super().__init__(
            message=f"Invalid image format: {reason}",
            code="INVALID_IMAGE_ERROR",
            details=details,
        )


class ExtractionError(IngestionException):
    """LLM extraction failed."""

    def __init__(self, image_url: str, llm: str, reason: str = ""):
        details = {"image_url": image_url, "llm": llm, "reason": reason}
        super().__init__(
            message=f"Content extraction failed: {reason}",
            code="EXTRACTION_ERROR",
            details=details,
        )


class EmbeddingError(IngestionException):
    """Embedding generation failed."""

    def __init__(self, reason: str = ""):
        super().__init__(
            message=f"Embedding generation failed: {reason}",
            code="EMBEDDING_ERROR",
            details={"reason": reason},
        )


class DatabaseError(IngestionException):
    """Database operation failed."""

    def __init__(self, operation: str, reason: str = ""):
        details = {"operation": operation, "reason": reason}
        super().__init__(
            message=f"Database {operation} failed: {reason}",
            code="DATABASE_ERROR",
            details=details,
        )


class RetryExhaustedError(IngestionException):
    """All retry attempts exhausted."""

    def __init__(self, operation: str, attempts: int):
        details = {"operation": operation, "attempts": attempts}
        super().__init__(
            message=f"Operation '{operation}' failed after {attempts} attempts",
            code="RETRY_EXHAUSTED",
            details=details,
        )
