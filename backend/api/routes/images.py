"""Image proxy API routes for serving Google Drive images."""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import io
from typing import Optional

from services.google_drive_service import get_drive_service
from exceptions.ingestion_exceptions import ImageDownloadError
from utils.retry_utils import with_retry, RetryConfig


router = APIRouter()


@router.get("/images/gdrive/{file_id}")
async def get_google_drive_image(file_id: str) -> Response:
    """
    Proxy endpoint to serve images from Google Drive.

    This endpoint authenticates with Google Drive using credentials.json and token.pickle,
    downloads the image, and returns it with proper content-type headers.

    Args:
        file_id: Google Drive file ID

    Returns:
        Image content with appropriate content-type

    Raises:
        HTTPException: If file not found, authentication fails, or download fails
    """
    try:
        # Get Google Drive service
        drive_service = get_drive_service()

        # Ensure authentication
        if not drive_service.is_authenticated():
            try:
                drive_service.authenticate(headless=True)
            except RuntimeError:
                raise HTTPException(
                    status_code=503,
                    detail="Google Drive authentication required. Please authenticate the service first."
                )

        # Get file metadata to determine MIME type
        try:
            file_metadata = await drive_service.get_file_metadata(file_id)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"File not found or inaccessible: {str(e)}"
            )

        # Download file content
        try:
            file_bytes = await drive_service.download_file(file_id)
        except ImageDownloadError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download image: {str(e)}"
            )

        # Return image with proper content type
        return Response(
            content=file_bytes,
            media_type=file_metadata.mime_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f'inline; filename="{file_metadata.name}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error serving image: {str(e)}"
        )
