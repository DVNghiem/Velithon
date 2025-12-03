"""Tests for SQLAlchemy adapter and repository pattern."""

import pytest
import pytest_asyncio
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from velithon.database import (
    Base,
    Database,
    SQLiteConfig,
    BaseRepository,
    get_model_columns,
    get_model_primary_keys,
)


class TestProduct(Base):
    """Test product model."""

    __tablename__ = "test_products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    price: Mapped[float] = mapped_column()
    stock: Mapped[int] = mapped_column(default=0)


class TestSQLAlchemyAdapter:
    """Tests for SQLAlchemy adapter."""

    def test_base_table_name(self):
        """Test automatic table name generation."""
        assert TestProduct.__tablename__ == "test_products"

    def test_to_dict(self):
        """Test model to_dict method."""
        product = TestProduct(id=1, name="Test", price=9.99, stock=10)
        data = product.to_dict()
        
        assert data["id"] == 1
        assert data["name"] == "Test"
        assert data["price"] == 9.99
        assert data["stock"] == 10

    def test_update_from_dict(self):
        """Test update_from_dict method."""
        product = TestProduct(id=1, name="Test", price=9.99, stock=10)
        product.update_from_dict({"name": "Updated", "price": 19.99})
        
        assert product.name == "Updated"
        assert product.price == 19.99

    def test_get_model_columns(self):
        """Test getting model columns."""
        columns = get_model_columns(TestProduct)
        assert "id" in columns
        assert "name" in columns
        assert "price" in columns
        assert "stock" in columns

    def test_get_model_primary_keys(self):
        """Test getting model primary keys."""
        pks = get_model_primary_keys(TestProduct)
        assert "id" in pks


class TestBaseRepository:
    """Tests for BaseRepository."""

    @pytest_asyncio.fixture
    async def database(self):
        """Create test database."""
        config = SQLiteConfig(database=":memory:")
        db = Database(config)
        await db.connect()
        
        # Create tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        yield db
        
        await db.disconnect()

    @pytest_asyncio.fixture
    async def session(self, database):
        """Create test session."""
        async with database.session() as session:
            yield session

    @pytest.fixture
    def repository(self, session):
        """Create test repository."""
        return BaseRepository(TestProduct, session)

    @pytest.mark.asyncio
    async def test_create(self, repository, session):
        """Test creating a record."""
        product = await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        
        assert product.id is not None
        assert product.name == "Test Product"
        assert product.price == 29.99
        assert product.stock == 100

    @pytest.mark.asyncio
    async def test_get(self, repository, session):
        """Test getting a record by ID."""
        # Create a product
        product = await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        await session.commit()
        
        # Get the product
        found = await repository.get(product.id)
        assert found is not None
        assert found.id == product.id
        assert found.name == "Test Product"

    @pytest.mark.asyncio
    async def test_get_by(self, repository, session):
        """Test getting a record by filters."""
        # Create a product
        await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        await session.commit()
        
        # Get by name
        found = await repository.get_by(name="Test Product")
        assert found is not None
        assert found.name == "Test Product"

    @pytest.mark.asyncio
    async def test_get_all(self, repository, session):
        """Test getting all records."""
        # Create multiple products
        await repository.create(name="Product 1", price=10.0, stock=5)
        await repository.create(name="Product 2", price=20.0, stock=10)
        await repository.create(name="Product 3", price=30.0, stock=15)
        await session.commit()
        
        # Get all
        products = await repository.get_all()
        assert len(products) == 3

    @pytest.mark.asyncio
    async def test_update(self, repository, session):
        """Test updating a record."""
        # Create a product
        product = await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        await session.commit()
        
        # Update the product
        updated = await repository.update(
            product.id,
            price=39.99,
            stock=50,
        )
        await session.commit()
        
        assert updated is not None
        assert updated.price == 39.99
        assert updated.stock == 50

    @pytest.mark.asyncio
    async def test_delete(self, repository, session):
        """Test deleting a record."""
        # Create a product
        product = await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        await session.commit()
        
        # Delete the product
        deleted = await repository.delete(product.id)
        await session.commit()
        
        assert deleted is True
        
        # Verify it's gone
        found = await repository.get(product.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_count(self, repository, session):
        """Test counting records."""
        # Create multiple products
        await repository.create(name="Product 1", price=10.0, stock=5)
        await repository.create(name="Product 2", price=20.0, stock=10)
        await session.commit()
        
        count = await repository.count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_exists(self, repository, session):
        """Test checking if records exist."""
        # Create a product
        await repository.create(
            name="Test Product",
            price=29.99,
            stock=100,
        )
        await session.commit()
        
        exists = await repository.exists(name="Test Product")
        assert exists is True
        
        not_exists = await repository.exists(name="Nonexistent")
        assert not_exists is False

    @pytest.mark.asyncio
    async def test_paginate(self, repository, session):
        """Test pagination."""
        # Create multiple products
        for i in range(25):
            await repository.create(
                name=f"Product {i}",
                price=float(i),
                stock=i,
            )
        await session.commit()
        
        # Get first page
        page1 = await repository.paginate(page=1, page_size=10)
        assert len(page1["items"]) == 10
        assert page1["total"] == 25
        assert page1["page"] == 1
        assert page1["total_pages"] == 3
        assert page1["has_next"] is True
        assert page1["has_prev"] is False
        
        # Get second page
        page2 = await repository.paginate(page=2, page_size=10)
        assert len(page2["items"]) == 10
        assert page2["page"] == 2
        assert page2["has_next"] is True
        assert page2["has_prev"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
