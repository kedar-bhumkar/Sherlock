"""Knowledge API routes."""

from fastapi import APIRouter, HTTPException, Query

from schemas.knowledge_schemas import (
    KnowledgeResponse,
    KnowledgeListResponse,
    RetryRequest,
    RetryResponse,
)
from schemas.common_schemas import ErrorResponse, PaginationMeta
from db.repositories.knowledge_repo import KnowledgeRepository
from db.models.knowledge import KnowledgeStatus
from services.ingestion_service import IngestionService
from exceptions.base import AppException

router = APIRouter()


@router.get(
    "/knowledge",
    response_model=KnowledgeListResponse,
    summary="List knowledge records",
    description="Get paginated list of knowledge records with optional filters",
)
async def list_knowledge(
    category: str = Query(default="All", description="Filter by category"),
    subcategory: str = Query(default="All", description="Filter by subcategory"),
    topic: str = Query(default="All", description="Filter by topic"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> KnowledgeListResponse:
    """List knowledge records with pagination and filters."""
    repo = KnowledgeRepository()

    offset = (page - 1) * page_size
    records, total = await repo.get_all(
        limit=page_size,
        offset=offset,
        category=category if category != "All" else None,
        subcategory=subcategory if subcategory != "All" else None,
        topic=topic if topic != "All" else None,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    data = [
        KnowledgeResponse(
            id=r.id,
            category=r.category,
            subcategory=r.subcategory,
            topic=r.topic,
            title=r.title,
            raw_data=r.raw_data,
            paraphrased_data=r.paraphrased_data,
            image=r.image,
            url=r.url,
            status=r.status,
            last_error=r.last_error,
            comments=r.comments,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]

    return KnowledgeListResponse(
        data=data,
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/knowledge/{record_id}",
    response_model=KnowledgeResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get single knowledge record",
    description="Get details of a specific knowledge record",
)
async def get_knowledge(record_id: str) -> KnowledgeResponse:
    """Get a single knowledge record by ID."""
    repo = KnowledgeRepository()
    record = await repo.get_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return KnowledgeResponse(
        id=record.id,
        category=record.category,
        subcategory=record.subcategory,
        topic=record.topic,
        title=record.title,
        raw_data=record.raw_data,
        paraphrased_data=record.paraphrased_data,
        image=record.image,
        url=record.url,
        status=record.status,
        last_error=record.last_error,
        comments=record.comments,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post(
    "/knowledge/{record_id}/retry",
    response_model=RetryResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="Retry failed record",
    description="Retry processing for a single failed record",
)
async def retry_record(record_id: str) -> RetryResponse:
    """Retry processing a failed record."""
    service = IngestionService()

    try:
        await service.retry_record(record_id)
        return RetryResponse(count=1, job_ids=[record_id])
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/knowledge/retry-failed",
    response_model=RetryResponse,
    summary="Retry all failed records",
    description="Batch retry all records with failed status",
)
async def retry_all_failed(request: RetryRequest) -> RetryResponse:
    """Retry all failed records."""
    service = IngestionService()
    repo = KnowledgeRepository()

    try:
        # Get failed records
        failed = await repo.get_failed(limit=request.limit)
        if request.category:
            failed = [r for r in failed if r.category == request.category]

        # Retry each
        job_ids = []
        for record in failed:
            await service.retry_record(record.id)
            job_ids.append(record.id)

        return RetryResponse(count=len(job_ids), job_ids=job_ids)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete(
    "/knowledge/{record_id}",
    responses={404: {"model": ErrorResponse}},
    summary="Delete knowledge record",
    description="Delete a knowledge record by ID",
)
async def delete_knowledge(record_id: str) -> dict:
    """Delete a knowledge record."""
    repo = KnowledgeRepository()
    deleted = await repo.delete(record_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")

    return {"deleted": True, "id": record_id}
