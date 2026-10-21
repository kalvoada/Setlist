"""
Bring the database schema up to date, as `alembic upgrade head` does.

Development databases used to be created with ``create_all``, which records no
migration revision, so Alembic would try to create their tables again. Those
are first marked with the revision their columns match.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from ..config import settings

logger = logging.getLogger(__name__)

_MIGRATIONS = Path(__file__).resolve().parents[2] / "migrations"


def alembic_config() -> Config:
    # No alembic.ini: its logging setup would silence the app's loggers.
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    return config


def upgrade_database() -> None:
    config = alembic_config()
    revision = _revision_of_unversioned_schema()
    if revision:
        logger.info("Marking the existing database as migration %s", revision)
        command.stamp(config, revision)
    command.upgrade(config, "head")


def _revision_of_unversioned_schema() -> Optional[str]:
    """The migration an unversioned database's tables match; None if not needed."""
    engine = create_engine(settings.database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        if "alembic_version" in tables or "users" not in tables:
            return None
        users = {column["name"] for column in inspector.get_columns("users")}
        music = {column["name"] for column in inspector.get_columns("music_items")}
    finally:
        engine.dispose()

    if "embed_url" in music:
        return "0003_embeds_and_link_cache"
    if "native_provider" in users and "provider_links" in music:
        return "0002_native_provider"
    return "0001_initial"
