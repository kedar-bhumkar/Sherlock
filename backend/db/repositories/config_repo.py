"""Repository for Config table operations."""

import asyncio
from typing import Optional

from supabase import Client

from db.models.config import Config, CategoryConfig, SubcategoryConfig, LLMConfig, TagsConfig
from db.repositories.base import BaseRepository
from db.supabase_client import get_supabase_client

# Module-level lock for atomic category updates
_tags_lock = asyncio.Lock()


class ConfigRepository(BaseRepository[Config]):
    """Repository for Config CRUD operations."""

    TABLE_NAME = "config"

    def __init__(self, client: Client | None = None):
        """
        Initialize repository.

        Args:
            client: Supabase client (uses singleton if not provided)
        """
        self.client = client or get_supabase_client()

    async def get_by_id(self, id: str) -> Optional[Config]:
        """Get config record by ID."""
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*")
            .eq("id", id)
            .single()
            .execute()
        )
        if response.data:
            return Config(**response.data)
        return None

    async def get_by_key(self, key: str) -> Optional[Config]:
        """Get config record by key."""
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*")
            .eq("key", key)
            .single()
            .execute()
        )
        if response.data:
            return Config(**response.data)
        return None

    async def get_all(
        self, limit: int = 100, offset: int = 0, **filters
    ) -> tuple[list[Config], int]:
        """Get all config records."""
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*", count="exact")
            .range(offset, offset + limit - 1)
            .execute()
        )
        records = [Config(**row) for row in response.data]
        total = response.count or 0
        return records, total

    async def get_tags(self) -> TagsConfig:
        """Get tags configuration."""
        config = await self.get_by_key("tags")
        if config:
            return TagsConfig(**config.value)
        # Return default if not configured
        return TagsConfig(categories=[])

    async def get_llms(self) -> LLMConfig:
        """Get LLM configuration."""
        config = await self.get_by_key("llms")
        if config:
            return LLMConfig(**config.value)
        # Return default if not configured
        return LLMConfig(web=[], local=[])

    async def create(self, entity: Config) -> Config:
        """Create a new config record."""
        data = entity.model_dump(exclude={"id"})
        response = self.client.table(self.TABLE_NAME).insert(data).execute()
        return Config(**response.data[0])

    async def update(self, id: str, entity: Config) -> Config:
        """Update an existing config record."""
        data = entity.model_dump(exclude={"id"})
        response = (
            self.client.table(self.TABLE_NAME).update(data).eq("id", id).execute()
        )
        return Config(**response.data[0])

    async def upsert_by_key(self, key: str, value: dict) -> Config:
        """Create or update config by key."""
        existing = await self.get_by_key(key)
        if existing:
            existing.value = value
            return await self.update(existing.id, existing)
        else:
            config = Config(key=key, value=value)
            return await self.create(config)

    async def delete(self, id: str) -> bool:
        """Delete a config record."""
        response = self.client.table(self.TABLE_NAME).delete().eq("id", id).execute()
        return len(response.data) > 0

    async def add_category_hierarchy(
        self,
        category_name: str,
        subcategory_name: str,
        topic_name: str,
    ) -> tuple[bool, bool, bool, TagsConfig]:
        """
        Atomically add new category, subcategory, and/or topic.

        Uses asyncio.Lock to prevent race conditions when multiple
        ingestions try to add the same hierarchy.

        Args:
            category_name: Name of the category (will be normalized to Title Case)
            subcategory_name: Name of the subcategory (will be normalized to lowercase)
            topic_name: Name of the topic (will be normalized to lowercase)

        Returns:
            Tuple of (category_added, subcategory_added, topic_added, updated_config)
        """
        async with _tags_lock:
            tags_config = await self.get_tags()
            category_added = False
            subcategory_added = False
            topic_added = False

            # Normalize names
            normalized_cat = category_name.strip().title()
            normalized_subcat = subcategory_name.strip().lower()
            normalized_topic = topic_name.strip().lower()

            # Find existing category (case-insensitive)
            category = next(
                (c for c in tags_config.categories if c.name.lower() == normalized_cat.lower()),
                None
            )

            if not category:
                # Create new category with subcategory and topic
                topics = (
                    [normalized_topic, "other"]
                    if normalized_topic != "other"
                    else ["other"]
                )
                subcategory = SubcategoryConfig(
                    name=normalized_subcat,
                    topics=topics,
                )
                category = CategoryConfig(
                    name=normalized_cat,
                    subcategories=[subcategory],
                )
                tags_config.categories.append(category)
                category_added = True
                subcategory_added = True
                topic_added = normalized_topic != "other"
            else:
                # Category exists - find or create subcategory
                subcategory = next(
                    (s for s in category.subcategories if s.name.lower() == normalized_subcat.lower()),
                    None
                )

                if not subcategory:
                    # Create new subcategory with topic
                    topics = (
                        [normalized_topic, "other"]
                        if normalized_topic != "other"
                        else ["other"]
                    )
                    subcategory = SubcategoryConfig(
                        name=normalized_subcat,
                        topics=topics,
                    )
                    category.subcategories.append(subcategory)
                    subcategory_added = True
                    topic_added = normalized_topic != "other"
                else:
                    # Subcategory exists - check if topic needs to be added
                    existing_topics = [t.lower() for t in subcategory.topics]
                    if normalized_topic not in existing_topics:
                        # Insert new topic before "other" if it exists
                        if "other" in subcategory.topics:
                            idx = subcategory.topics.index("other")
                            subcategory.topics.insert(idx, normalized_topic)
                        else:
                            subcategory.topics.append(normalized_topic)
                        topic_added = True

            # Persist to database if anything changed
            if category_added or subcategory_added or topic_added:
                await self.upsert_by_key("tags", tags_config.model_dump())

            return category_added, subcategory_added, topic_added, tags_config
