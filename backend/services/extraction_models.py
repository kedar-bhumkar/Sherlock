"""Pydantic models for LLM extraction response structure."""

from pydantic import BaseModel, Field


class ConceptDetail(BaseModel):
    """A single concept with its expanded information."""

    concept: str = Field(description="High-level concept name")
    expanded_information: str = Field(description="Detailed information about the concept")


class ParaphrasedData(BaseModel):
    """Structured paraphrased data with summary and concept details."""

    summary: str = Field(
        description="Summary of what is present in the image (brief description of the flow, architecture, or key concept)"
    )
    details: list[ConceptDetail] = Field(
        description="List of key concepts with their expanded information"
    )


class CategoryField(BaseModel):
    """Category/subcategory/topic field with new indicator."""

    value: str = Field(description="The category/subcategory/topic value")
    is_new: bool = Field(default=False, description="Whether this is a newly created entry")


class ExtractionResponse(BaseModel):
    """Complete extraction response from LLM."""

    raw_data: str = Field(
        description="ALL text and content visible in the image, extracted thoroughly and accurately"
    )
    paraphrased_data: ParaphrasedData = Field(
        description="Structured paraphrased version of the content"
    )
    title: str = Field(description="Short, descriptive title (5-10 words maximum)")
    category: CategoryField = Field(description="Category classification (Title Case)")
    subcategory: CategoryField = Field(description="Subcategory classification (lowercase)")
    topic: CategoryField = Field(description="Topic classification (lowercase)")


def get_json_schema() -> dict:
    """Get the JSON schema for extraction response."""
    return ExtractionResponse.model_json_schema()


def get_schema_example() -> str:
    """Get an example JSON structure for the prompt."""
    return """{
  "raw_data": "Extract ALL text and content visible in the image. Be thorough and accurate.",
  "paraphrased_data": {
    "summary": "Summary of what is present in the image (e.g., brief description of the flow, architecture, or key concept depicted like roadmap, strategy, pricing comparison, etc.)",
    "details": [
      {
        "concept": "High-level concept",
        "expanded_information": "Detailed information about the concept"
      }
    ]
  },
  "title": "Create a short, descriptive title (5-10 words maximum)",
  "category": {
    "value": "Category name (Title Case)",
    "is_new": false
  },
  "subcategory": {
    "value": "subcategory name (lowercase)",
    "is_new": false
  },
  "topic": {
    "value": "topic name (lowercase)",
    "is_new": false
  }
}"""
