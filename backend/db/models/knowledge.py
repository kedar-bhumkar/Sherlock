"""Knowledge model representing extracted image content."""

import json
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class KnowledgeStatus(str, Enum):
    """Status of a knowledge record."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Knowledge(BaseModel):
    """Knowledge record from image extraction."""

    id: str | None = Field(default=None, description="Primary key")
    category: str = Field(..., description="Category from config tags")
    subcategory: str = Field(..., description="Subcategory from config tags")
    topic: str = Field(default="general", description="Topic from config tags")
    title: str = Field(..., description="Short, meaningful title")
    raw_data: str = Field(..., description="Raw extracted text from image")
    paraphrased_data: str = Field(..., description="Paraphrased version of extracted text")
    image: str = Field(..., description="Image URL or path")
    url: str = Field(default="", description="Source URL if applicable")
    status: KnowledgeStatus = Field(
        default=KnowledgeStatus.PENDING, description="Processing status"
    )
    last_error: str | None = Field(
        default=None, description="Error details if status is failed"
    )
    comments: str | None = Field(
        default=None, description="Additional comments or error context"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    embedding: list[float] | None = Field(
        default=None, description="Vector embedding (3072 dimensions)"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")

    @field_validator("embedding", mode="before")
    @classmethod
    def parse_embedding(cls, v):
        """Parse string representation of embedding from DB if needed."""
        if isinstance(v, str):
            try:
                # Remove brackets and split by comma or use json.loads
                if v.startswith("[") and v.endswith("]"):
                    return json.loads(v)
            except Exception:
                # Fallback to default pydantic handling if parsing fails
                pass
        return v

    class Config:
        use_enum_values = True
