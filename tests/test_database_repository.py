"""Comprehensive tests for database repository pattern.

This module tests the BaseRepository class including CRUD operations,
bulk operations, filtering, pagination, and error handling.
"""

import pytest
import pytest_asyncio
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from velithon.database import Base, Database, SQLiteConfig
from velithon.database.repository import BaseRepository


class Product(Base):
    """Test product model for repository tests."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column()
    category: Mapped[str] = mapped_column(String(50))
    in_stock: Mapped[bool] = mapped_column(default=True)


class TestBaseRepository:
    """Tests for BaseRepository CRUD operations."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create test database with products table."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()

        # Create tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield db

        await db.disconnect()

    @pytest_asyncio.fixture
    async def repository(self, database):
        """Create product repository."""
        async with database.session() as session:
            yield BaseRepository(Product, session)

    @pytest.mark.asyncio
    async def test_create_single(self, database):
        """Test creating a single record."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            product = await repo.create(
                name="Laptop",
                price=999.99,
                category="Electronics",
                in_stock=True
            )
            
            assert product.id is not None
            assert product.name == "Laptop"
            assert product.price == 999.99
            assert product.category == "Electronics"
            assert product.in_stock is True

    @pytest.mark.asyncio
    async def test_create_many(self, database):
        """Test creating multiple records."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            products = await repo.create_many([
                {"name": "Mouse", "price": 29.99, "category": "Electronics", "in_stock": True},
                {"name": "Keyboard", "price": 79.99, "category": "Electronics", "in_stock": True},
                {"name": "Monitor", "price": 299.99, "category": "Electronics", "in_stock": False},
            ])
            
            assert len(products) == 3
            assert all(p.id is not None for p in products)
            assert products[0].name == "Mouse"
            assert products[1].name == "Keyboard"
            assert products[2].name == "Monitor"

    @pytest.mark.asyncio
    async def test_get_by_id(self, database):
        """Test getting a record by ID."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create product
            created = await repo.create(
                name="Tablet",
                price=499.99,
                category="Electronics",
                in_stock=True
            )
            await session.commit()
            
            # Get by ID
            product = await repo.get(created.id)
            
            assert product is not None
            assert product.id == created.id
            assert product.name == "Tablet"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, database):
        """Test getting a non-existent record."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            product = await repo.get(99999)
            
            assert product is None

    @pytest.mark.asyncio
    async def test_get_by_filters(self, database):
        """Test getting a record by filters."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products
            await repo.create(name="Phone", price=699.99, category="Electronics", in_stock=True)
            await session.commit()
            
            # Get by filters
            product = await repo.get_by(name="Phone", category="Electronics")
            
            assert product is not None
            assert product.name == "Phone"
            assert product.category == "Electronics"

    @pytest.mark.asyncio
    async def test_get_all(self, database):
        """Test getting all records."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create multiple products
            await repo.create_many([
                {"name": "Product1", "price": 10.00, "category": "Cat1", "in_stock": True},
                {"name": "Product2", "price": 20.00, "category": "Cat2", "in_stock": True},
                {"name": "Product3", "price": 30.00, "category": "Cat1", "in_stock": False},
            ])
            await session.commit()
            
            # Get all
            products = await repo.get_all()
            
            assert len(products) == 3

    @pytest.mark.asyncio
    async def test_get_all_with_filters(self, database):
        """Test getting records with filters."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products
            await repo.create_many([
                {"name": "Product1", "price": 10.00, "category": "Cat1", "in_stock": True},
                {"name": "Product2", "price": 20.00, "category": "Cat2", "in_stock": True},
                {"name": "Product3", "price": 30.00, "category": "Cat1", "in_stock": False},
            ])
            await session.commit()
            
            # Get with filter
            products = await repo.get_all(category="Cat1")
            
            assert len(products) == 2
            assert all(p.category == "Cat1" for p in products)

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(self, database):
        """Test pagination with limit and offset."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create 10 products
            await repo.create_many([
                {"name": f"Product{i}", "price": float(i), "category": "Test", "in_stock": True}
                for i in range(10)
            ])
            await session.commit()
            
            # Get with limit
            products = await repo.get_all(limit=5)
            assert len(products) == 5
            
            # Get with offset
            products = await repo.get_all(limit=5, offset=5)
            assert len(products) == 5

    @pytest.mark.asyncio
    async def test_update_by_id(self, database):
        """Test updating a record by ID."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create product
            product = await repo.create(
                name="OldName",
                price=100.00,
                category="OldCategory",
                in_stock=True
            )
            await session.commit()
            
            # Update
            updated = await repo.update(product.id, name="NewName", price=150.00)
            await session.commit()
            
            assert updated is not None
            assert updated.name == "NewName"
            assert updated.price == 150.00
            assert updated.category == "OldCategory"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_not_found(self, database):
        """Test updating a non-existent record."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            updated = await repo.update(99999, name="NewName")
            
            assert updated is None

    @pytest.mark.asyncio
    async def test_update_many(self, database):
        """Test updating multiple records."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products
            await repo.create_many([
                {"name": "Product1", "price": 10.00, "category": "OldCat", "in_stock": True},
                {"name": "Product2", "price": 20.00, "category": "OldCat", "in_stock": True},
                {"name": "Product3", "price": 30.00, "category": "Other", "in_stock": True},
            ])
            await session.commit()
            
            # Update multiple
            count = await repo.update_many(
                filters={"category": "OldCat"},
                values={"category": "NewCat"}
            )
            await session.commit()
            
            assert count == 2
            
            # Verify updates
            products = await repo.get_all(category="NewCat")
            assert len(products) == 2

    @pytest.mark.asyncio
    async def test_delete_by_id(self, database):
        """Test deleting a record by ID."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create product
            product = await repo.create(
                name="ToDelete",
                price=100.00,
                category="Test",
                in_stock=True
            )
            await session.commit()
            product_id = product.id
            
            # Delete
            deleted = await repo.delete(product_id)
            await session.commit()
            
            assert deleted is True
            
            # Verify deletion
            product = await repo.get(product_id)
            assert product is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, database):
        """Test deleting a non-existent record."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            deleted = await repo.delete(99999)
            
            assert deleted is False

    @pytest.mark.asyncio
    async def test_delete_many(self, database):
        """Test deleting multiple records."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products
            await repo.create_many([
                {"name": "Product1", "price": 10.00, "category": "ToDelete", "in_stock": True},
                {"name": "Product2", "price": 20.00, "category": "ToDelete", "in_stock": True},
                {"name": "Product3", "price": 30.00, "category": "Keep", "in_stock": True},
            ])
            await session.commit()
            
            # Delete multiple
            count = await repo.delete_many(category="ToDelete")
            await session.commit()
            
            assert count == 2
            
            # Verify deletions
            products = await repo.get_all()
            assert len(products) == 1
            assert products[0].category == "Keep"

    @pytest.mark.asyncio
    async def test_count(self, database):
        """Test counting records."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products
            await repo.create_many([
                {"name": "Product1", "price": 10.00, "category": "Cat1", "in_stock": True},
                {"name": "Product2", "price": 20.00, "category": "Cat1", "in_stock": True},
                {"name": "Product3", "price": 30.00, "category": "Cat2", "in_stock": True},
            ])
            await session.commit()
            
            # Count all
            count = await repo.count()
            assert count == 3
            
            # Count with filter
            count = await repo.count(category="Cat1")
            assert count == 2

    @pytest.mark.asyncio
    async def test_exists(self, database):
        """Test checking if records exist."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Initially empty
            exists = await repo.exists()
            assert exists is False
            
            # Create product
            await repo.create(
                name="Product",
                price=10.00,
                category="Test",
                in_stock=True
            )
            await session.commit()
            
            # Should exist
            exists = await repo.exists()
            assert exists is True
            
            # Exists with matching filter
            exists = await repo.exists(category="Test")
            assert exists is True
            
            # Does not exist with non-matching filter
            exists = await repo.exists(category="NonExistent")
            assert exists is False

    @pytest.mark.asyncio
    async def test_paginate(self, database):
        """Test pagination."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create 25 products
            await repo.create_many([
                {"name": f"Product{i}", "price": float(i), "category": "Test", "in_stock": True}
                for i in range(25)
            ])
            await session.commit()
            
            # First page
            result = await repo.paginate(page=1, page_size=10)
            
            assert len(result["items"]) == 10
            assert result["total"] == 25
            assert result["page"] == 1
            assert result["page_size"] == 10
            assert result["total_pages"] == 3
            assert result["has_next"] is True
            assert result["has_prev"] is False
            
            # Second page
            result = await repo.paginate(page=2, page_size=10)
            
            assert len(result["items"]) == 10
            assert result["page"] == 2
            assert result["has_next"] is True
            assert result["has_prev"] is True
            
            # Last page
            result = await repo.paginate(page=3, page_size=10)
            
            assert len(result["items"]) == 5
            assert result["page"] == 3
            assert result["has_next"] is False
            assert result["has_prev"] is True

    @pytest.mark.asyncio
    async def test_paginate_with_filters(self, database):
        """Test pagination with filters."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create products with different categories
            await repo.create_many([
                {"name": f"Product{i}", "price": float(i), "category": "Cat1" if i % 2 == 0 else "Cat2", "in_stock": True}
                for i in range(20)
            ])
            await session.commit()
            
            # Paginate with filter
            result = await repo.paginate(page=1, page_size=5, category="Cat1")
            
            assert len(result["items"]) == 5
            assert result["total"] == 10  # Only Cat1 products
            assert all(p.category == "Cat1" for p in result["items"])

    @pytest.mark.asyncio
    async def test_refresh(self, database):
        """Test refreshing a model instance."""
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            
            # Create product
            product = await repo.create(
                name="Original",
                price=100.00,
                category="Test",
                in_stock=True
            )
            await session.commit()
            
            # Modify locally (not committed)
            product.name = "Modified"
            
            # Refresh from database
            refreshed = await repo.refresh(product)
            
            assert refreshed.name == "Original"  # Should revert to DB value

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, database):
        """Test concurrent repository operations."""
        import asyncio
        
        async def create_product(db, index):
            async with db.session() as session:
                repo = BaseRepository(Product, session)
                product = await repo.create(
                    name=f"Product{index}",
                    price=float(index),
                    category="Test",
                    in_stock=True
                )
                await session.commit()
                return product
        
        # Create 10 products concurrently
        tasks = [create_product(database, i) for i in range(10)]
        products = await asyncio.gather(*tasks)
        
        assert len(products) == 10
        assert all(p.id is not None for p in products)
        
        # Verify all products were created
        async with database.session() as session:
            repo = BaseRepository(Product, session)
            count = await repo.count()
            assert count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
