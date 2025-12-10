"""Database migration utilities for Velithon.

This module provides integration with Alembic for database migrations.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manager for database migrations using Alembic.

    This class provides a high-level interface for managing database migrations.
    """

    def __init__(
        self,
        database_url: str,
        migrations_dir: str = "migrations",
        script_location: str | None = None,
    ):
        """Initialize the migration manager.

        Args:
            database_url: Database connection URL
            migrations_dir: Directory for migration files
            script_location: Custom script location (defaults to migrations_dir)

        """
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir)
        self.script_location = script_location or str(self.migrations_dir)

    def _get_alembic_config(self) -> AlembicConfig:
        """Get Alembic configuration.

        Returns:
            AlembicConfig instance

        """
        # Create alembic config
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option("script_location", self.script_location)
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)

        # Set additional options
        alembic_cfg.set_main_option(
            "file_template", "%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s"  # noqa: E501
        )

        return alembic_cfg

    def init(self, template: str = "async") -> None:
        """Initialize migration directory.

        Args:
            template: Alembic template to use (default: 'async' for async support)

        """
        logger.info(f"Initializing migrations in {self.migrations_dir}")

        alembic_cfg = self._get_alembic_config()
        command.init(alembic_cfg, str(self.migrations_dir), template=template)

        logger.info("Migrations initialized successfully")

    def create_migration(
        self,
        message: str,
        *,
        autogenerate: bool = True,
    ) -> None:
        """Create a new migration.

        Args:
            message: Migration message/description
            autogenerate: Whether to auto-generate migration from model changes

        """
        logger.info(f"Creating migration: {message}")

        alembic_cfg = self._get_alembic_config()
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=autogenerate,
        )

        logger.info("Migration created successfully")

    def upgrade(self, revision: str = "head") -> None:
        """Upgrade database to a specific revision.

        Args:
            revision: Target revision (default: 'head' for latest)

        """
        logger.info(f"Upgrading database to {revision}")

        alembic_cfg = self._get_alembic_config()
        command.upgrade(alembic_cfg, revision)

        logger.info("Database upgraded successfully")

    def downgrade(self, revision: str = "-1") -> None:
        """Downgrade database to a specific revision.

        Args:
            revision: Target revision (default: '-1' for one step back)

        """
        logger.info(f"Downgrading database to {revision}")

        alembic_cfg = self._get_alembic_config()
        command.downgrade(alembic_cfg, revision)

        logger.info("Database downgraded successfully")

    def current(self) -> None:
        """Show current database revision."""
        alembic_cfg = self._get_alembic_config()
        command.current(alembic_cfg)

    def history(self, verbose: bool = False) -> None:
        """Show migration history.

        Args:
            verbose: Whether to show verbose output

        """
        alembic_cfg = self._get_alembic_config()
        command.history(alembic_cfg, verbose=verbose)

    def stamp(self, revision: str) -> None:
        """Stamp database with a specific revision without running migrations.

        Args:
            revision: Target revision

        """
        logger.info(f"Stamping database with revision {revision}")

        alembic_cfg = self._get_alembic_config()
        command.stamp(alembic_cfg, revision)

        logger.info("Database stamped successfully")

    def show(self, revision: str) -> None:
        """Show details of a specific migration.

        Args:
            revision: Migration revision

        """
        alembic_cfg = self._get_alembic_config()
        command.show(alembic_cfg, revision)

    def merge(self, revisions: list[str], message: str | None = None) -> None:
        """Merge multiple revisions.

        Args:
            revisions: List of revisions to merge
            message: Merge message

        """
        logger.info(f"Merging revisions: {', '.join(revisions)}")

        alembic_cfg = self._get_alembic_config()
        command.merge(alembic_cfg, revisions, message=message)

        logger.info("Revisions merged successfully")


def get_migration_template() -> str:
    """Get the async migration template for Alembic.

    Returns:
        Migration template content

    """
    return '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database schema."""
    ${downgrades if downgrades else "pass"}
'''
