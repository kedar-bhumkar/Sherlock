"""Ingestion API routes."""

from fastapi import APIRouter, HTTPException

from schemas.ingest_schemas import IngestRequest, IngestResponse, JobStatusResponse
from schemas.common_schemas import ErrorResponse
from services.ingestion_service import IngestionService
from services.google_drive_service import get_drive_service
from db.repositories.knowledge_repo import KnowledgeRepository
from exceptions.base import AppException

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Ingest images for processing",
    description="Queue images from URL, local folder, or Google Drive for content extraction",
)
async def ingest_images(request: IngestRequest) -> IngestResponse:
    """
    Ingest images for processing.

    Supports:
    - Single image from URL (image_url)
    - Batch images from local folder (folder_type="local", folder_location)
    - Single image from Google Drive (image_url with drive.google.com link)
    - Batch images from Google Drive folder (folder_type="google_drive", folder_location)
    """
    print(f"[Ingest] POST /ingest: request received")
    print(f"[Ingest] POST /ingest: image_url={request.image_url}")
    print(f"[Ingest] POST /ingest: folder_type={request.folder_type}, folder_location={request.folder_location}")
    print(f"[Ingest] POST /ingest: llm_type={request.llm_type}, llm={request.llm}")

    service = IngestionService(llm_type=request.llm_type, llm_id=request.llm)
    job_ids = []

    try:
        # Check if it's a Google Drive URL
        is_google_drive_url = request.image_url and "drive.google.com" in request.image_url
        print(f"[Ingest] POST /ingest: is_google_drive_url={is_google_drive_url}")

        if request.image_url and not is_google_drive_url:
            # Single image from regular URL
            print(f"[Ingest] POST /ingest: ingesting from regular URL")
            job_id = await service.ingest_from_url(request.image_url)
            job_ids.append(job_id)
            print(f"[Ingest] POST /ingest: created job_id={job_id}")

        elif is_google_drive_url:
            # Single image from Google Drive URL
            print(f"[Ingest] POST /ingest: ingesting from Google Drive URL")
            job_ids = await _ingest_from_google_drive_url(service, request.image_url)
            print(f"[Ingest] POST /ingest: created {len(job_ids)} jobs from Google Drive URL")

        elif request.folder_type == "local" and request.folder_location:
            # Batch from local folder
            print(f"[Ingest] POST /ingest: ingesting from local folder: {request.folder_location}")
            job_ids = await service.ingest_from_local_folder(request.folder_location)
            print(f"[Ingest] POST /ingest: created {len(job_ids)} jobs from local folder")

        elif request.folder_type == "google_drive":
            # Batch from Google Drive folder
            if not request.folder_location:
                print("[Ingest] POST /ingest: ERROR - folder_location required for Google Drive")
                raise HTTPException(
                    status_code=400,
                    detail="folder_location (folder ID or URL) is required for Google Drive",
                )

            print(f"[Ingest] POST /ingest: ingesting from Google Drive folder: {request.folder_location}")
            job_ids = await _ingest_from_google_drive_folder(service, request.folder_location)
            print(f"[Ingest] POST /ingest: created {len(job_ids)} jobs from Google Drive folder")

        else:
            print("[Ingest] POST /ingest: ERROR - invalid request parameters")
            raise HTTPException(
                status_code=400,
                detail="Must provide either image_url or folder_type with folder_location",
            )

        print(f"[Ingest] POST /ingest: SUCCESS - returning {len(job_ids)} job IDs")
        return IngestResponse(
            job_ids=job_ids,
            count=len(job_ids),
            status="processing",
        )

    except AppException as e:
        print(f"[Ingest] POST /ingest: AppException - {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)


def _ensure_drive_authenticated():
    """Ensure Google Drive is authenticated."""
    print("[Ingest] _ensure_drive_authenticated: checking authentication")

    drive_service = get_drive_service()

    if not drive_service.is_configured():
        print(f"[Ingest] _ensure_drive_authenticated: ERROR - credentials.json not found at {drive_service.credentials_path}")
        raise HTTPException(
            status_code=400,
            detail=f"Google Drive not configured. Place credentials.json at {drive_service.credentials_path}",
        )

    if drive_service.needs_authentication():
        print("[Ingest] _ensure_drive_authenticated: needs authentication, trying headless refresh")
        # Try headless auth first (token refresh)
        try:
            drive_service.authenticate(headless=True)
            print("[Ingest] _ensure_drive_authenticated: headless auth succeeded")
        except RuntimeError as e:
            print(f"[Ingest] _ensure_drive_authenticated: ERROR - headless auth failed: {e}")
            raise HTTPException(
                status_code=401,
                detail="Google Drive not authenticated. Call POST /api/auth/google/authenticate first.",
            )

    print("[Ingest] _ensure_drive_authenticated: SUCCESS - authenticated")


async def _ingest_from_google_drive_url(
    service: IngestionService, url: str
) -> list[str]:
    """Ingest a single file from Google Drive URL."""
    print(f"[Ingest] _ingest_from_google_drive_url: url={url}")

    _ensure_drive_authenticated()
    drive_service = get_drive_service()

    # Extract file ID from URL
    file_id = drive_service.extract_file_id_from_url(url)
    if not file_id:
        print("[Ingest] _ingest_from_google_drive_url: ERROR - could not extract file ID")
        raise HTTPException(
            status_code=400,
            detail="Could not extract file ID from Google Drive URL",
        )

    print(f"[Ingest] _ingest_from_google_drive_url: extracted file_id={file_id}")

    # Check if it's a folder
    folder_id = drive_service.extract_folder_id_from_url(url)
    if folder_id and "/folders/" in url:
        # It's a folder URL, ingest all files
        print(f"[Ingest] _ingest_from_google_drive_url: detected folder URL, folder_id={folder_id}")
        return await _ingest_files_from_folder(service, drive_service, folder_id)

    # It's a file URL, ingest single file
    print("[Ingest] _ingest_from_google_drive_url: processing as single file")
    return await _ingest_single_drive_file(service, drive_service, file_id)


async def _ingest_from_google_drive_folder(
    service: IngestionService, folder_location: str
) -> list[str]:
    """Ingest all images from a Google Drive folder."""
    print(f"[Ingest] _ingest_from_google_drive_folder: folder_location={folder_location}")

    _ensure_drive_authenticated()
    drive_service = get_drive_service()

    # Extract folder ID (could be URL or direct ID)
    if "drive.google.com" in folder_location:
        folder_id = drive_service.extract_folder_id_from_url(folder_location)
        print(f"[Ingest] _ingest_from_google_drive_folder: extracted folder_id={folder_id} from URL")
    else:
        folder_id = folder_location  # Assume it's a direct folder ID
        print(f"[Ingest] _ingest_from_google_drive_folder: using direct folder_id={folder_id}")

    if not folder_id:
        print("[Ingest] _ingest_from_google_drive_folder: ERROR - could not extract folder ID")
        raise HTTPException(
            status_code=400,
            detail="Could not extract folder ID from Google Drive URL",
        )

    return await _ingest_files_from_folder(service, drive_service, folder_id)


async def _ingest_files_from_folder(
    service: IngestionService, drive_service, folder_id: str
) -> list[str]:
    """List and ingest all image files from a Google Drive folder."""
    print(f"[Ingest] _ingest_files_from_folder: listing files in folder_id={folder_id}")

    # List all image files in folder
    files = await drive_service.list_files_in_folder(folder_id, images_only=True)

    if not files:
        print("[Ingest] _ingest_files_from_folder: ERROR - no image files found")
        raise HTTPException(
            status_code=404,
            detail="No image files found in the Google Drive folder",
        )

    print(f"[Ingest] _ingest_files_from_folder: found {len(files)} image files")

    job_ids = []
    success_count = 0
    failure_count = 0

    for i, file in enumerate(files):
        print(f"[Ingest] _ingest_files_from_folder: processing file {i+1}/{len(files)}: {file.name}")
        try:
            file_job_ids = await _ingest_single_drive_file(service, drive_service, file.id)
            job_ids.extend(file_job_ids)
            success_count += 1
        except Exception as e:
            failure_count += 1
            print(f"[Ingest] _ingest_files_from_folder: ERROR processing {file.name}: {e}")
            print(f"[Ingest] _ingest_files_from_folder: skipping file and continuing with next")

    print(f"[Ingest] _ingest_files_from_folder: COMPLETE - {success_count} succeeded, {failure_count} failed out of {len(files)} files")
    return job_ids


async def _ingest_single_drive_file(
    service: IngestionService, drive_service, file_id: str
) -> list[str]:
    """Download and ingest a single file from Google Drive."""
    print(f"[Ingest] _ingest_single_drive_file: file_id={file_id}")

    # Get file metadata
    print("[Ingest] _ingest_single_drive_file: fetching file metadata")
    file_metadata = await drive_service.get_file_metadata(file_id)
    print(f"[Ingest] _ingest_single_drive_file: file name={file_metadata.name}, type={file_metadata.mime_type}")

    # Download file content
    print("[Ingest] _ingest_single_drive_file: downloading file content")
    image_bytes = await drive_service.download_file(file_id)
    print(f"[Ingest] _ingest_single_drive_file: downloaded {len(image_bytes)} bytes")

    # Create ingestion record with Google Drive source
    print("[Ingest] _ingest_single_drive_file: creating ingestion record")
    job_id = await service.ingest_from_bytes(
        image_bytes=image_bytes,
        source_url=file_metadata.web_view_link or f"https://drive.google.com/file/d/{file_id}/view",
        filename=file_metadata.name,
    )
    print(f"[Ingest] _ingest_single_drive_file: SUCCESS - job_id={job_id}")

    return [job_id]


@router.get(
    "/ingest/{job_id}/status",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get job status",
    description="Check the processing status of an ingestion job",
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get the status of an ingestion job."""
    print(f"[Ingest] GET /ingest/{job_id}/status: checking job status")

    repo = KnowledgeRepository()
    record = await repo.get_by_id(job_id)

    if not record:
        print(f"[Ingest] GET /ingest/{job_id}/status: ERROR - job not found")
        raise HTTPException(status_code=404, detail="Job not found")

    print(f"[Ingest] GET /ingest/{job_id}/status: status={record.status}, error={record.last_error}")

    return JobStatusResponse(
        job_id=job_id,
        status=record.status,
        error=record.last_error,
        retry_count=record.retry_count,
    )
