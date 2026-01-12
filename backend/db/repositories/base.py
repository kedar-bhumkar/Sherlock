"""Base repository with common CRUD operations."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class BaseRepository(Generic[T], ABC):
    """Abstract base repository defining standard CRUD operations."""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get a single record by ID.

        Args:
            id: Record primary key

        Returns:
            Record if found, None otherwise
        """
        ...

    @abstractmethod
    async def get_all(
        self, limit: int = 100, offset: int = 0, **filters
    ) -> tuple[list[T], int]:
        """
        Get all records with pagination and optional filters.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            **filters: Additional filter criteria

        Returns:
            Tuple of (list of records, total count)
        """
        ...

    @abstractmethod
    async def create(self, entity: T) -> T:
        """
        Create a new record.

        Args:
            entity: Record to create

        Returns:
            Created record with ID
        """
        ...

    @abstractmethod
    async def update(self, id: str, entity: T) -> T:
        """
        Update an existing record.

        Args:
            id: Record primary key
            entity: Updated record data

        Returns:
            Updated record
        """
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Record primary key

        Returns:
            True if deleted, False otherwise
        """
        ...
