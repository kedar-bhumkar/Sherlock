"""Image handling utilities."""

import base64
from pathlib import Path
from typing import Optional

import httpx

from exceptions.ingestion_exceptions import ImageDownloadError, InvalidImageError

# Supported image MIME types
SUPPORTED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
}

# Flatten extensions for validation
SUPPORTED_EXTENSIONS = {ext for exts in SUPPORTED_MIME_TYPES.values() for ext in exts}


async def download_image(url: str, timeout: float = 30.0) -> bytes:
    """
    Download image from URL.

    Args:
        url: Image URL
        timeout: Request timeout in seconds

    Returns:
        Image bytes

    Raises:
        ImageDownloadError: If download fails
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if not any(mime in content_type for mime in SUPPORTED_MIME_TYPES):
                raise InvalidImageError(url, f"Unsupported content type: {content_type}")

            return response.content

    except httpx.TimeoutException:
        raise ImageDownloadError(url, "Request timed out")
    except httpx.HTTPStatusError as e:
        raise ImageDownloadError(url, f"HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        raise ImageDownloadError(url, str(e))


def get_image_from_path(path: str) -> bytes:
    """
    Read image from local filesystem.

    Args:
        path: Local file path

    Returns:
        Image bytes

    Raises:
        ImageDownloadError: If file cannot be read
        InvalidImageError: If file extension is not supported
    """
    file_path = Path(path)

    if not file_path.exists():
        raise ImageDownloadError(path, "File not found")

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise InvalidImageError(path, f"Unsupported extension: {file_path.suffix}")

    try:
        return file_path.read_bytes()
    except IOError as e:
        raise ImageDownloadError(path, str(e))


def validate_image(image_bytes: bytes) -> bool:
    """
    Validate image bytes by checking magic numbers.

    Args:
        image_bytes: Raw image bytes

    Returns:
        True if valid image

    Raises:
        InvalidImageError: If image format is invalid
    """
    if len(image_bytes) < 8:
        raise InvalidImageError("", "Image too small")

    # Check magic numbers
    magic_numbers = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89PNG\r\n\x1a\n": "PNG",
        b"GIF87a": "GIF",
        b"GIF89a": "GIF",
        b"RIFF": "WEBP",  # WEBP starts with RIFF
    }

    for magic, format_name in magic_numbers.items():
        if image_bytes.startswith(magic):
            return True

    # Special check for WEBP (RIFF....WEBP)
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return True

    raise InvalidImageError("", "Unknown image format")


def image_to_base64(image_bytes: bytes) -> str:
    """
    Convert image bytes to base64 string.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Base64 encoded string
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def get_mime_type(image_bytes: bytes) -> Optional[str]:
    """
    Detect MIME type from image bytes.

    Args:
        image_bytes: Raw image bytes

    Returns:
        MIME type string or None
    """
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    elif image_bytes.startswith(b"GIF"):
        return "image/gif"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None
