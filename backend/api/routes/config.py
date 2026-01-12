"""Config API routes."""

from fastapi import APIRouter

from db.repositories.config_repo import ConfigRepository
from db.models.config import TagsConfig, LLMConfig

router = APIRouter()


@router.get(
    "/config/tags",
    response_model=TagsConfig,
    summary="Get tags configuration",
    description="Get available categories and subcategories",
)
async def get_tags() -> TagsConfig:
    """Get tags configuration."""
    repo = ConfigRepository()
    return await repo.get_tags()


@router.get(
    "/config/llms",
    response_model=LLMConfig,
    summary="Get LLM configuration",
    description="Get available LLM providers",
)
async def get_llms() -> LLMConfig:
    """Get LLM configuration."""
    repo = ConfigRepository()
    return await repo.get_llms()


@router.get(
    "/config",
    summary="Get all configuration",
    description="Get all configuration settings",
)
async def get_all_config() -> dict:
    """Get all configuration."""
    repo = ConfigRepository()
    tags = await repo.get_tags()
    llms = await repo.get_llms()

    return {
        "tags": tags.model_dump(),
        "llms": llms.model_dump(),
    }
