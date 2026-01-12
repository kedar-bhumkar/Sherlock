"""Schemas for ingestion endpoints."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request body for image ingestion."""

    folder_type: Literal["local", "google_drive"] | None = Field(
        default=None, description="Type of folder source"
    )
    folder_location: str | None = Field(
        default=None, description="Path, URL to folder, or Google Drive folder ID/URL"
    )
    image_url: str | None = Field(
        default=None, description="Single image URL or Google Drive file link"
    )
    llm_type: Literal["local", "web"] = Field(
        default="web", description="Type of LLM to use"
    )
    llm: str = Field(
        default="gemini-3-flash-preview", description="LLM identifier"
    )


class IngestResponse(BaseModel):
    """Response from ingestion endpoint."""

    job_ids: list[str] = Field(..., description="List of job IDs for tracking")
    count: int = Field(..., description="Number of images queued for processing")
    status: str = Field(default="processing", description="Current status")


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="Current status")
    error: str | None = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retry attempts")
