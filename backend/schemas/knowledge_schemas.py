"""Schemas for knowledge endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeResponse(BaseModel):
    """Single knowledge record response."""

    id: str = Field(..., description="Record ID")
    category: str = Field(..., description="Category")
    subcategory: str = Field(..., description="Subcategory")
    topic: str = Field(default="general", description="Topic")
    title: str = Field(..., description="Title")
    raw_data: str = Field(..., description="Raw extracted text")
    paraphrased_data: str = Field(..., description="Paraphrased text")
    image: str = Field(..., description="Image URL or path")
    url: str = Field(..., description="Source URL")
    status: str = Field(..., description="Processing status")
    last_error: str | None = Field(default=None, description="Error details if failed")
    comments: str | None = Field(default=None, description="Additional comments or error context")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Update timestamp")


class KnowledgeListResponse(BaseModel):
    """Paginated list of knowledge records."""

    data: list[KnowledgeResponse] = Field(..., description="Knowledge records")
    meta: dict = Field(..., description="Pagination metadata")


class RetryRequest(BaseModel):
    """Request for retry operation."""

    category: str | None = Field(default=None, description="Filter by category")
    limit: int = Field(default=100, ge=1, le=1000, description="Max records to retry")


class RetryResponse(BaseModel):
    """Response from retry operation."""

    count: int = Field(..., description="Number of records queued for retry")
    job_ids: list[str] = Field(default_factory=list, description="Job IDs for tracking")
