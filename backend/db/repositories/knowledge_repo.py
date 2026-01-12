"""Repository for Knowledge table operations."""

from typing import Optional
from supabase import Client

from db.models.knowledge import Knowledge, KnowledgeStatus
from db.repositories.base import BaseRepository
from db.supabase_client import get_supabase_client


class KnowledgeRepository(BaseRepository[Knowledge]):
    """Repository for Knowledge CRUD operations."""

    TABLE_NAME = "knowledge"

    def __init__(self, client: Client | None = None):
        """
        Initialize repository.

        Args:
            client: Supabase client (uses singleton if not provided)
        """
        self.client = client or get_supabase_client()

    async def get_by_id(self, id: str) -> Optional[Knowledge]:
        """Get knowledge record by ID."""
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*")
            .eq("id", id)
            .single()
            .execute()
        )
        if response.data:
            return Knowledge(**response.data)
        return None

    async def get_by_image(self, image: str) -> Optional[Knowledge]:
        """
        Get knowledge record by image URL or path.

        Args:
            image: Image URL or local file path

        Returns:
            Knowledge record if found, None otherwise
        """
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*")
            .eq("image", image)
            .limit(1)
            .execute()
        )
        if response.data:
            return Knowledge(**response.data[0])
        return None

    async def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
        subcategory: str | None = None,
        topic: str | None = None,
        status: KnowledgeStatus | None = None,
    ) -> tuple[list[Knowledge], int]:
        """
        Get all knowledge records with pagination and filters.

        Args:
            limit: Page size
            offset: Number of records to skip
            category: Filter by category
            subcategory: Filter by subcategory
            topic: Filter by topic
            status: Filter by status

        Returns:
            Tuple of (list of Knowledge, total count)
        """
        query = self.client.table(self.TABLE_NAME).select("*", count="exact")

        if category and category.lower() != "all":
            query = query.eq("category", category)
        if subcategory and subcategory.lower() != "all":
            query = query.eq("subcategory", subcategory)
        if topic and topic.lower() != "all":
            query = query.eq("topic", topic)
        if status:
            query = query.eq("status", status.value)

        response = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        records = [Knowledge(**row) for row in response.data]
        total = response.count or 0

        return records, total

    async def get_failed(self, limit: int = 100) -> list[Knowledge]:
        """Get all failed records for retry."""
        response = (
            self.client.table(self.TABLE_NAME)
            .select("*")
            .eq("status", KnowledgeStatus.FAILED.value)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [Knowledge(**row) for row in response.data]

    async def create(self, entity: Knowledge) -> Knowledge:
        """Create a new knowledge record."""
        data = entity.model_dump(exclude={"id", "created_at", "updated_at"})
        # Remove None embedding to let DB handle default
        if data.get("embedding") is None:
            del data["embedding"]

        response = self.client.table(self.TABLE_NAME).insert(data).execute()
        return Knowledge(**response.data[0])

    async def update(self, id: str, entity: Knowledge) -> Knowledge:
        """Update an existing knowledge record."""
        data = entity.model_dump(exclude={"id", "created_at"})
        response = (
            self.client.table(self.TABLE_NAME).update(data).eq("id", id).execute()
        )
        return Knowledge(**response.data[0])

    async def update_status(
        self,
        id: str,
        status: KnowledgeStatus,
        error: str | None = None,
        comments: str | None = None,
        increment_retry: bool = False,
    ) -> Knowledge:
        """
        Update record status.

        Args:
            id: Record ID
            status: New status
            error: Error message if failed
            comments: Additional comments or error context
            increment_retry: Whether to increment retry count
        """
        data = {"status": status.value, "last_error": error}

        if comments is not None:
            data["comments"] = comments

        if increment_retry:
            # Fetch current retry count and increment
            current = await self.get_by_id(id)
            if current:
                data["retry_count"] = current.retry_count + 1

        response = (
            self.client.table(self.TABLE_NAME).update(data).eq("id", id).execute()
        )
        return Knowledge(**response.data[0])

    async def update_with_extraction(
        self,
        id: str,
        raw_data: str,
        paraphrased_data: str,
        title: str,
        category: str,
        subcategory: str,
        topic: str,
        embedding: list[float],
    ) -> Knowledge:
        """Update record with LLM extraction results."""
        data = {
            "raw_data": raw_data,
            "paraphrased_data": paraphrased_data,
            "title": title,
            "category": category,
            "subcategory": subcategory,
            "topic": topic,
            "embedding": embedding,
            "status": KnowledgeStatus.COMPLETED.value,
            "last_error": None,
        }
        response = (
            self.client.table(self.TABLE_NAME).update(data).eq("id", id).execute()
        )
        return Knowledge(**response.data[0])

    async def reset_for_reprocessing(self, id: str) -> Knowledge:
        """
        Reset a record to pending status for reprocessing.

        Clears previous extraction data and resets status.

        Args:
            id: Record ID

        Returns:
            Updated Knowledge record
        """
        data = {
            "status": KnowledgeStatus.PENDING.value,
            "category": "",
            "subcategory": "",
            "topic": "general",
            "title": "",
            "raw_data": "",
            "paraphrased_data": "",
            "embedding": None,
            "last_error": None,
            "comments": "Reprocessing - URL/image already existed",
            "retry_count": 0,
        }
        response = (
            self.client.table(self.TABLE_NAME).update(data).eq("id", id).execute()
        )
        return Knowledge(**response.data[0])

    async def delete(self, id: str) -> bool:
        """Delete a knowledge record."""
        response = self.client.table(self.TABLE_NAME).delete().eq("id", id).execute()
        return len(response.data) > 0

    async def semantic_search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.5,
        category: str | None = None,
        subcategory: str | None = None,
        topic: str | None = None,
    ) -> list[tuple[Knowledge, float]]:
        """
        Perform semantic similarity search using pgvector.

        Args:
            query_embedding: Query embedding vector (1536 dimensions)
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1, cosine similarity)
            category: Optional category filter
            subcategory: Optional subcategory filter
            topic: Optional topic filter

        Returns:
            List of (Knowledge, similarity_score) tuples, ordered by similarity
        """
        # Build the RPC params for pgvector match function
        params = {
            "query_embedding": query_embedding,
            "match_threshold": similarity_threshold,
            "match_count": limit,
        }

        # Add optional filters
        if category and category.lower() != "all":
            params["filter_category"] = category
        if subcategory and subcategory.lower() != "all":
            params["filter_subcategory"] = subcategory
        if topic and topic.lower() != "all":
            params["filter_topic"] = topic

        # Call the Supabase RPC function for vector similarity search
        response = self.client.rpc("match_knowledge", params).execute()

        results = []
        for row in response.data:
            # Extract similarity score and create Knowledge object
            similarity = row.pop("similarity", 0.0)
            knowledge = Knowledge(**row)
            results.append((knowledge, similarity))

        return results

    async def semantic_search_simple(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[tuple[Knowledge, float]]:
        """
        Simple semantic search without filters using direct SQL via RPC.

        This is a fallback if the filtered RPC function doesn't exist.

        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results

        Returns:
            List of (Knowledge, similarity_score) tuples
        """
        params = {
            "query_embedding": query_embedding,
            "match_count": limit,
        }

        response = self.client.rpc("match_knowledge_simple", params).execute()

        results = []
        for row in response.data:
            similarity = row.pop("similarity", 0.0)
            knowledge = Knowledge(**row)
            results.append((knowledge, similarity))

        return results
