"""Development databases are brought up to date on startup."""

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from src.config import settings
from src.database.migrate import alembic_config, upgrade_database

HEAD = "0004_reset_link_cache"


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/dev.db"
    monkeypatch.setattr(settings, "database_url", url)
    engine = create_engine(url)
    yield engine
    engine.dispose()


def at(engine, revision: str, *, recorded: bool = True) -> None:
    """A database whose tables match ``revision``; ``recorded=False`` is one
    built by create_all, with no record of which migration it's at."""
    command.upgrade(alembic_config(), revision)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (username, email, hashed_password, bio, is_active, "
            "created_at, updated_at) VALUES ('adam', 'adam@example.com', 'x', '', 1, "
            "'2026-01-01', '2026-01-01')"
        ))
        if not recorded:
            connection.execute(text("DROP TABLE alembic_version"))


def version(engine) -> str:
    with engine.connect() as connection:
        query = text("SELECT version_num FROM alembic_version")
        return connection.execute(query).scalar()


def music_columns(engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("music_items")}


@pytest.mark.parametrize(
    "revision", ["0001_initial", "0002_native_provider", HEAD]
)
def test_an_unrecorded_database_is_upgraded_and_keeps_its_data(database, revision):
    at(database, revision, recorded=False)

    upgrade_database()

    assert version(database) == HEAD
    assert "embed_url" in music_columns(database)
    with database.connect() as connection:
        assert connection.execute(text("SELECT username FROM users")).scalar() == "adam"


def test_a_recorded_database_is_upgraded(database):
    at(database, "0002_native_provider")

    upgrade_database()

    assert version(database) == HEAD
    assert "embed_url" in music_columns(database)


def test_a_new_database_is_created(database):
    upgrade_database()

    assert version(database) == HEAD
    assert "users" in inspect(database).get_table_names()


def test_an_up_to_date_database_is_left_alone(database):
    at(database, HEAD)

    upgrade_database()
    upgrade_database()

    assert version(database) == HEAD
