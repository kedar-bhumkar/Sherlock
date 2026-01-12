"""Config models for application configuration stored in Supabase."""

from pydantic import BaseModel, Field


class LLMProvider(BaseModel):
    """Single LLM provider configuration."""

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Display name")
    provider: str = Field(..., description="Provider name (openai, anthropic, google, ollama)")
    model: str = Field(..., description="Model identifier")
    default: bool = Field(default=False, description="Is this the default LLM")


class LLMConfig(BaseModel):
    """LLM configuration with web and local providers."""

    web: list[LLMProvider] = Field(default_factory=list, description="Web-based LLM providers")
    local: list[LLMProvider] = Field(default_factory=list, description="Local LLM providers (Ollama)")


class SubcategoryConfig(BaseModel):
    """Subcategory with topics."""

    name: str = Field(..., description="Subcategory name")
    topics: list[str] = Field(default_factory=list, description="Topic names")


class CategoryConfig(BaseModel):
    """Category with subcategories."""

    name: str = Field(..., description="Category name")
    subcategories: list[SubcategoryConfig] = Field(
        default_factory=list, description="Subcategories with topics"
    )


class TagsConfig(BaseModel):
    """Tags configuration with categories and subcategories."""

    categories: list[CategoryConfig] = Field(
        default_factory=list, description="Available categories"
    )


class Config(BaseModel):
    """Configuration record stored in Supabase."""

    id: str | None = Field(default=None, description="Primary key")
    key: str = Field(..., description="Configuration key (tags, llms)")
    value: dict = Field(..., description="Configuration value as JSON")
