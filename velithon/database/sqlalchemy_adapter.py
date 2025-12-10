"""SQLAlchemy adapter and utilities for Velithon.

This module provides SQLAlchemy-specific utilities including
declarative base setup and query helpers.
"""

from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, declared_attr

# Naming convention for constraints
NAMING_CONVENTION = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all SQLAlchemy models.

    This class provides async attribute loading and common utilities
    for all database models.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name.

        Converts CamelCase to snake_case and pluralizes.
        """
        import re

        # Convert CamelCase to snake_case
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()

        # Simple pluralization (add 's')
        # For more complex pluralization, consider using inflect library
        if not name.endswith('s'):
            name += 's'

        return name

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.

        Returns:
            Dictionary representation of the model

        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def update_from_dict(self, data: dict[str, Any]) -> None:
        """Update model instance from dictionary.

        Args:
            data: Dictionary with attribute values

        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self) -> str:
        """Return string representation of the model.

        Returns:
            String representation

        """
        attrs = ', '.join(
            f'{col.name}={getattr(self, col.name)!r}' for col in self.__table__.columns
        )
        return f'{self.__class__.__name__}({attrs})'


def get_model_columns(model: type[Base]) -> list[str]:
    """Get list of column names for a model.

    Args:
        model: SQLAlchemy model class

    Returns:
        List of column names

    """
    return [column.name for column in model.__table__.columns]


def get_model_primary_keys(model: type[Base]) -> list[str]:
    """Get list of primary key column names for a model.

    Args:
        model: SQLAlchemy model class

    Returns:
        List of primary key column names

    """
    return [column.name for column in model.__table__.primary_key.columns]


def get_model_relationships(model: type[Base]) -> list[str]:
    """Get list of relationship names for a model.

    Args:
        model: SQLAlchemy model class

    Returns:
        List of relationship names

    """
    from sqlalchemy.orm import class_mapper

    mapper = class_mapper(model)
    return [rel.key for rel in mapper.relationships]
