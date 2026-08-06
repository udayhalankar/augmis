from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.dialects import postgresql

from app import db_models  # noqa: F401
from app.core.config import settings
from app.core.database import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

AUTOGENERATE_EXCLUDED_TABLES = {
    "connector_files",
    "connector_sync_failures",
    "connector_sync_runs",
    "runtime_auth_challenges",
    "runtime_auth_state",
}

AUTOGENERATE_EXCLUDED_COLUMNS = {
    ("documents", "connector_file_id"),
    ("documents", "external_file_id"),
    ("documents", "file_hash"),
    ("documents", "is_current_version"),
    ("documents", "is_deleted"),
    ("documents", "source_modified_at"),
    ("documents", "source_type"),
    ("documents", "version_number"),
    ("repositories", "connection_config"),
    ("repositories", "last_sync_run_id"),
    ("repositories", "sync_enabled"),
    ("repositories", "sync_metadata"),
    ("repositories", "sync_status"),
}


def include_object(object_, name, type_, reflected, compare_to):
    if type_ == "table" and name in AUTOGENERATE_EXCLUDED_TABLES:
        return False

    if type_ == "column":
        table_name = getattr(getattr(object_, "table", None), "name", None)
        if table_name and (table_name, name) in AUTOGENERATE_EXCLUDED_COLUMNS:
            return False

    return True


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    table_name = getattr(getattr(metadata_column, "table", None), "name", None)
    column_name = getattr(metadata_column, "name", None)

    if table_name and column_name and (table_name, column_name) in AUTOGENERATE_EXCLUDED_COLUMNS:
        return False

    if isinstance(inspected_type, postgresql.TIMESTAMP) and getattr(metadata_type, "timezone", False):
        return False

    if isinstance(inspected_type, postgresql.JSONB) and metadata_type.__class__.__name__ == "JSON":
        return False

    return None


def compare_server_default(
    context,
    inspected_column,
    metadata_column,
    inspected_default,
    metadata_default,
    rendered_metadata_default,
):
    table_name = getattr(getattr(metadata_column, "table", None), "name", None)
    column_name = getattr(metadata_column, "name", None)

    if table_name and column_name and (table_name, column_name) in AUTOGENERATE_EXCLUDED_COLUMNS:
        return False

    return None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=compare_type,
        compare_server_default=compare_server_default,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=compare_type,
            compare_server_default=compare_server_default,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
