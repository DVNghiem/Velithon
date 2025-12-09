"""Repository pattern implementation for Velithon.

This module provides base repository classes for implementing
the repository pattern with SQLAlchemy models.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from velithon.database.sqlalchemy_adapter import Base

ModelType = TypeVar('ModelType', bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository for CRUD operations.

    This class provides common database operations for SQLAlchemy models
    following the repository pattern.
    """

    def __init__(self, model: type[ModelType], session: AsyncSession):
        """Initialize the repository.

        Args:
            model: SQLAlchemy model class
            session: Database session

        """
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelType | None:
        """Get a single record by ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found

        """
        return await self.session.get(self.model, id)

    async def get_by(self, **filters: Any) -> ModelType | None:
        """Get a single record by filters.

        Args:
            **filters: Column filters

        Returns:
            Model instance or None if not found

        """
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        **filters: Any,
    ) -> Sequence[ModelType]:
        """Get all records matching filters.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            **filters: Column filters

        Returns:
            List of model instances

        """
        stmt = select(self.model).filter_by(**filters)

        if offset is not None:
            stmt = stmt.offset(offset)

        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, **data: Any) -> ModelType:
        """Create a new record.

        Args:
            **data: Column values

        Returns:
            Created model instance

        """
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def create_many(self, items: list[dict[str, Any]]) -> list[ModelType]:
        """Create multiple records.

        Args:
            items: List of dictionaries with column values

        Returns:
            List of created model instances

        """
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        await self.session.flush()

        # Refresh all instances
        for instance in instances:
            await self.session.refresh(instance)

        return instances

    async def update(self, id: Any, **data: Any) -> ModelType | None:
        """Update a record by ID.

        Args:
            id: Primary key value
            **data: Column values to update

        Returns:
            Updated model instance or None if not found

        """
        instance = await self.get(id)
        if instance is None:
            return None

        for key, value in data.items():
            setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_many(self, **data: Any) -> int:
        """Update multiple records matching filters.

        Args:
            **data: Column values to update (must include filters)

        Returns:
            Number of updated records

        Example:
            # Update all users with status='active' to status='inactive'
            await repo.update_many(
                filters={'status': 'active'},
                values={'status': 'inactive'}
            )

        """
        filters = data.pop('filters', {})
        values = data.pop('values', data)

        stmt = update(self.model).filter_by(**filters).values(**values)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def delete(self, id: Any) -> bool:
        """Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found

        """
        instance = await self.get(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def delete_many(self, **filters: Any) -> int:
        """Delete multiple records matching filters.

        Args:
            **filters: Column filters

        Returns:
            Number of deleted records

        """
        stmt = delete(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def count(self, **filters: Any) -> int:
        """Count records matching filters.

        Args:
            **filters: Column filters

        Returns:
            Number of matching records

        """
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, **filters: Any) -> bool:
        """Check if any records match filters.

        Args:
            **filters: Column filters

        Returns:
            True if at least one record exists, False otherwise

        """
        count = await self.count(**filters)
        return count > 0

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> dict[str, Any]:
        """Get paginated results.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            **filters: Column filters

        Returns:
            Dictionary with pagination metadata and items

        """
        if page < 1:
            page = 1

        offset = (page - 1) * page_size

        # Get total count
        total = await self.count(**filters)

        # Get items for current page
        items = await self.get_all(limit=page_size, offset=offset, **filters)

        total_pages = (total + page_size - 1) // page_size

        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }

    async def refresh(self, instance: ModelType) -> ModelType:
        """Refresh a model instance from the database.

        Args:
            instance: Model instance to refresh

        Returns:
            Refreshed model instance

        """
        await self.session.refresh(instance)
        return instance
