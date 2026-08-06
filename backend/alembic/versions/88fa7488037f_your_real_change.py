"""Connector sync schema reconciliation.

Revision ID: 88fa7488037f
Revises: 13bf198836cf
Create Date: 2026-06-09 00:21:07.871849
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql



# revision identifiers, used by Alembic.
revision: str = '88fa7488037f'
down_revision: Union[str, Sequence[str], None] = '13bf198836cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_map(inspector, table_name: str) -> dict[str, dict]:
    return {column["name"]: column for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_key_names(inspector, table_name: str) -> set[str]:
    return {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}


def _unique_constraint_names(inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _is_varcharish(column_type) -> bool:
    return isinstance(column_type, (sa.String, sa.Text, postgresql.VARCHAR))


def _is_uuidish(column_type) -> bool:
    return isinstance(column_type, (sa.UUID, postgresql.UUID))


def _ensure_index(inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    if index_name not in _index_names(inspector, table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _ensure_unique_constraint(
    inspector,
    table_name: str,
    constraint_name: str,
    columns: list[str],
) -> None:
    if constraint_name not in _unique_constraint_names(inspector, table_name):
        op.create_unique_constraint(constraint_name, table_name, columns)


def _ensure_foreign_key(
    inspector,
    table_name: str,
    constraint_name: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    if constraint_name not in _foreign_key_names(inspector, table_name):
        op.create_foreign_key(
            constraint_name,
            table_name,
            referent_table,
            local_cols,
            remote_cols,
        )


def _drop_index_if_exists(inspector, table_name: str, index_name: str) -> None:
    if index_name in _index_names(inspector, table_name):
        op.drop_index(index_name, table_name=table_name)


def _rename_column_if_needed(inspector, table_name: str, old_name: str, new_name: str) -> None:
    columns = _column_map(inspector, table_name)
    if old_name in columns and new_name not in columns:
        op.alter_column(table_name, old_name, new_column_name=new_name)


def _ensure_column(inspector, table_name: str, column: sa.Column) -> None:
    if column.name not in _column_map(inspector, table_name):
        op.add_column(table_name, column)


def _alter_column_to_varchar(inspector, table_name: str, column_name: str) -> None:
    columns = _column_map(inspector, table_name)
    column = columns.get(column_name)
    if not column:
        return

    column_type = column["type"]
    if _is_varcharish(column_type):
        return

    if _is_uuidish(column_type):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
                f"TYPE VARCHAR USING {column_name}::text"
            )
        )
        return

    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
            f"TYPE VARCHAR USING {column_name}::text"
        )
    )


def _alter_column_to_timestamptz(inspector, table_name: str, column_name: str) -> None:
    columns = _column_map(inspector, table_name)
    column = columns.get(column_name)
    if not column:
        return

    column_type = column["type"]
    if getattr(column_type, "timezone", False):
        return

    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
            f"TYPE TIMESTAMPTZ USING {column_name} AT TIME ZONE 'UTC'"
        )
    )


def _ensure_default_and_not_null(table_name: str, column_name: str, default_sql: str) -> None:
    op.execute(
        sa.text(
            f'UPDATE "{table_name}" '
            f'SET "{column_name}" = {default_sql} '
            f'WHERE "{column_name}" IS NULL'
        )
    )
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" SET DEFAULT {default_sql}'
        )
    )
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" SET NOT NULL'
        )
    )


def _ensure_json_column_type(inspector, table_name: str, column_name: str) -> None:
    columns = _column_map(inspector, table_name)
    column = columns.get(column_name)
    if not column:
        return

    column_type = column["type"]
    if isinstance(column_type, postgresql.JSON):
        return

    if isinstance(column_type, postgresql.JSONB):
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" '
                f'TYPE JSON USING "{column_name}"::json'
            )
        )


def _empty_json_literal(inspector, table_name: str, column_name: str) -> str:
    column = _column_map(inspector, table_name).get(column_name)
    column_type = column["type"] if column else None
    if isinstance(column_type, postgresql.JSONB):
        return "'{}'::jsonb"
    return "'{}'::json"


def _create_connector_sync_runs() -> None:
    op.create_table(
        "connector_sync_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("repository_id", sa.String(), sa.ForeignKey("repositories.repository_id"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sync_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default=sa.text("'running'")),
        sa.Column("sync_mode", sa.String(length=50), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("files_discovered", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("files_skipped", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("files_deleted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("chunks_created", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("embeddings_created", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_by", sa.String(), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_connector_sync_runs_tenant_id", "connector_sync_runs", ["tenant_id"])
    op.create_index("ix_connector_sync_runs_repository_id", "connector_sync_runs", ["repository_id"])
    op.create_index("ix_connector_sync_runs_source_type", "connector_sync_runs", ["source_type"])
    op.create_index("ix_connector_sync_runs_sync_status", "connector_sync_runs", ["sync_status"])


def _create_connector_files() -> None:
    op.create_table(
        "connector_files",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("repository_id", sa.String(), sa.ForeignKey("repositories.repository_id"), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("external_file_id", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("last_sync_run_id", sa.String(), sa.ForeignKey("connector_sync_runs.id"), nullable=True),
        sa.Column("document_id", sa.String(), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_current_version", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "repository_id",
            "external_file_id",
            "version_number",
            name="uq_connector_file_version",
        ),
    )
    op.create_index("ix_connector_files_tenant_id", "connector_files", ["tenant_id"])
    op.create_index("ix_connector_files_repository_id", "connector_files", ["repository_id"])
    op.create_index("ix_connector_files_source_type", "connector_files", ["source_type"])
    op.create_index("ix_connector_files_sync_status", "connector_files", ["sync_status"])
    op.create_index("ix_connector_files_file_hash", "connector_files", ["file_hash"])
    op.create_index("ix_connector_files_is_deleted", "connector_files", ["is_deleted"])
    op.create_index("ix_connector_files_document_id", "connector_files", ["document_id"])
    op.create_index(
        "idx_connector_files_incremental",
        "connector_files",
        ["tenant_id", "repository_id", "external_file_id", "source_modified_at"],
    )
    op.create_index(
        "idx_connector_files_hash",
        "connector_files",
        ["tenant_id", "repository_id", "file_hash"],
    )


def _create_connector_sync_failures() -> None:
    op.create_table(
        "connector_sync_failures",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("tenant_id", sa.String(), sa.ForeignKey("tenants.tenant_id"), nullable=False),
        sa.Column("repository_id", sa.String(), sa.ForeignKey("repositories.repository_id"), nullable=False),
        sa.Column("sync_run_id", sa.String(), sa.ForeignKey("connector_sync_runs.id"), nullable=True),
        sa.Column("connector_file_id", sa.String(), sa.ForeignKey("connector_files.id"), nullable=True),
        sa.Column("external_file_id", sa.Text(), nullable=True),
        sa.Column("file_name", sa.Text(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("failure_stage", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_connector_sync_failures_tenant_id", "connector_sync_failures", ["tenant_id"])
    op.create_index("ix_connector_sync_failures_repository_id", "connector_sync_failures", ["repository_id"])
    op.create_index("ix_connector_sync_failures_sync_run_id", "connector_sync_failures", ["sync_run_id"])
    op.create_index("ix_connector_sync_failures_connector_file_id", "connector_sync_failures", ["connector_file_id"])
    op.create_index("ix_connector_sync_failures_resolved", "connector_sync_failures", ["resolved"])


def _reconcile_connector_sync_runs(inspector) -> None:
    _rename_column_if_needed(inspector, "connector_sync_runs", "created_by", "started_by")
    inspector = sa.inspect(op.get_bind())
    _ensure_column(inspector, "connector_sync_runs", sa.Column("sync_mode", sa.String(length=50), nullable=True))
    _ensure_column(inspector, "connector_sync_runs", sa.Column("files_skipped", sa.Integer(), nullable=True))
    _ensure_column(inspector, "connector_sync_runs", sa.Column("started_by", sa.String(), nullable=True))
    _ensure_column(inspector, "connector_sync_runs", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(op.get_bind())
    for column_name in ("id", "tenant_id", "repository_id", "started_by"):
        _alter_column_to_varchar(inspector, "connector_sync_runs", column_name)

    inspector = sa.inspect(op.get_bind())
    for column_name in ("sync_started_at", "sync_completed_at", "created_at"):
        _alter_column_to_timestamptz(inspector, "connector_sync_runs", column_name)

    _ensure_default_and_not_null("connector_sync_runs", "sync_mode", "'manual'")
    _ensure_default_and_not_null("connector_sync_runs", "files_discovered", "0")
    _ensure_default_and_not_null("connector_sync_runs", "files_processed", "0")
    _ensure_default_and_not_null("connector_sync_runs", "files_skipped", "0")
    _ensure_default_and_not_null("connector_sync_runs", "files_failed", "0")
    _ensure_default_and_not_null("connector_sync_runs", "files_deleted", "0")
    _ensure_default_and_not_null("connector_sync_runs", "chunks_created", "0")
    _ensure_default_and_not_null("connector_sync_runs", "embeddings_created", "0")

    op.execute(sa.text("UPDATE connector_sync_runs SET created_at = now() WHERE created_at IS NULL"))
    op.execute(sa.text("ALTER TABLE connector_sync_runs ALTER COLUMN created_at SET DEFAULT now()"))
    op.execute(sa.text("ALTER TABLE connector_sync_runs ALTER COLUMN created_at SET NOT NULL"))

    inspector = sa.inspect(op.get_bind())
    _drop_index_if_exists(inspector, "connector_sync_runs", "idx_connector_sync_runs_repo")
    _ensure_index(inspector, "connector_sync_runs", "ix_connector_sync_runs_tenant_id", ["tenant_id"])
    _ensure_index(inspector, "connector_sync_runs", "ix_connector_sync_runs_repository_id", ["repository_id"])
    _ensure_index(inspector, "connector_sync_runs", "ix_connector_sync_runs_source_type", ["source_type"])
    _ensure_index(inspector, "connector_sync_runs", "ix_connector_sync_runs_sync_status", ["sync_status"])
    _ensure_foreign_key(
        inspector,
        "connector_sync_runs",
        "fk_connector_sync_runs_tenant_id",
        "tenants",
        ["tenant_id"],
        ["tenant_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_sync_runs",
        "fk_connector_sync_runs_repository_id",
        "repositories",
        ["repository_id"],
        ["repository_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_sync_runs",
        "fk_connector_sync_runs_started_by",
        "users",
        ["started_by"],
        ["user_id"],
    )


def _reconcile_connector_files(inspector) -> None:
    _rename_column_if_needed(inspector, "connector_files", "metadata", "metadata_json")
    inspector = sa.inspect(op.get_bind())
    _ensure_column(inspector, "connector_files", sa.Column("first_synced_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("last_sync_run_id", sa.String(), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("is_current_version", sa.Boolean(), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("retry_count", sa.Integer(), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("last_error_message", sa.Text(), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("metadata_json", sa.JSON(), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "connector_files", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(op.get_bind())
    for column_name in ("id", "tenant_id", "repository_id", "document_id", "last_sync_run_id"):
        _alter_column_to_varchar(inspector, "connector_files", column_name)

    inspector = sa.inspect(op.get_bind())
    for column_name in (
        "source_created_at",
        "source_modified_at",
        "first_synced_at",
        "last_synced_at",
        "deleted_at",
        "created_at",
        "updated_at",
    ):
        _alter_column_to_timestamptz(inspector, "connector_files", column_name)

    _ensure_json_column_type(sa.inspect(op.get_bind()), "connector_files", "metadata_json")

    inspector = sa.inspect(op.get_bind())
    metadata_default = _empty_json_literal(inspector, "connector_files", "metadata_json")
    op.execute(sa.text("UPDATE connector_files SET first_synced_at = COALESCE(first_synced_at, last_synced_at, now())"))
    op.execute(sa.text(f"UPDATE connector_files SET metadata_json = COALESCE(metadata_json, {metadata_default})"))
    op.execute(sa.text("UPDATE connector_files SET created_at = COALESCE(created_at, now())"))
    op.execute(sa.text("UPDATE connector_files SET updated_at = COALESCE(updated_at, now())"))

    _ensure_default_and_not_null("connector_files", "sync_status", "'pending'")
    _ensure_default_and_not_null("connector_files", "version_number", "1")
    _ensure_default_and_not_null("connector_files", "is_current_version", "true")
    _ensure_default_and_not_null("connector_files", "is_deleted", "false")
    _ensure_default_and_not_null("connector_files", "retry_count", "0")

    op.execute(sa.text(f"ALTER TABLE connector_files ALTER COLUMN metadata_json SET DEFAULT {metadata_default}"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN metadata_json SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN first_synced_at SET DEFAULT now()"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN first_synced_at SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN created_at SET DEFAULT now()"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN created_at SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN updated_at SET DEFAULT now()"))
    op.execute(sa.text("ALTER TABLE connector_files ALTER COLUMN updated_at SET NOT NULL"))

    inspector = sa.inspect(op.get_bind())
    _ensure_index(inspector, "connector_files", "ix_connector_files_tenant_id", ["tenant_id"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_repository_id", ["repository_id"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_source_type", ["source_type"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_sync_status", ["sync_status"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_file_hash", ["file_hash"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_is_deleted", ["is_deleted"])
    _ensure_index(inspector, "connector_files", "ix_connector_files_document_id", ["document_id"])
    _ensure_index(
        inspector,
        "connector_files",
        "idx_connector_files_incremental",
        ["tenant_id", "repository_id", "external_file_id", "source_modified_at"],
    )
    _ensure_index(
        inspector,
        "connector_files",
        "idx_connector_files_hash",
        ["tenant_id", "repository_id", "file_hash"],
    )
    _ensure_unique_constraint(
        inspector,
        "connector_files",
        "uq_connector_file_version",
        ["tenant_id", "repository_id", "external_file_id", "version_number"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_files",
        "fk_connector_files_tenant_id",
        "tenants",
        ["tenant_id"],
        ["tenant_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_files",
        "fk_connector_files_repository_id",
        "repositories",
        ["repository_id"],
        ["repository_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_files",
        "fk_connector_files_document_id",
        "documents",
        ["document_id"],
        ["document_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_files",
        "fk_connector_files_last_sync_run_id",
        "connector_sync_runs",
        ["last_sync_run_id"],
        ["id"],
    )


def _reconcile_connector_sync_failures(inspector) -> None:
    inspector = sa.inspect(op.get_bind())
    _ensure_column(inspector, "connector_sync_failures", sa.Column("sync_run_id", sa.String(), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("external_file_id", sa.Text(), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("file_name", sa.Text(), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("file_path", sa.Text(), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("max_retries", sa.Integer(), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "connector_sync_failures", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    inspector = sa.inspect(op.get_bind())
    for column_name in ("id", "tenant_id", "repository_id", "connector_file_id", "sync_run_id"):
        _alter_column_to_varchar(inspector, "connector_sync_failures", column_name)

    inspector = sa.inspect(op.get_bind())
    for column_name in ("last_retry_at", "next_retry_at", "resolved_at", "created_at"):
        _alter_column_to_timestamptz(inspector, "connector_sync_failures", column_name)

    op.execute(
        sa.text(
            "ALTER TABLE connector_sync_failures "
            "ALTER COLUMN failure_stage TYPE VARCHAR(80) USING failure_stage::text"
        )
    )
    _ensure_default_and_not_null("connector_sync_failures", "retry_count", "0")
    _ensure_default_and_not_null("connector_sync_failures", "max_retries", "3")
    _ensure_default_and_not_null("connector_sync_failures", "resolved", "false")

    op.execute(
        sa.text(
            "UPDATE connector_sync_failures "
            "SET failure_stage = 'db_write' "
            "WHERE failure_stage IS NULL"
        )
    )
    op.execute(
        sa.text(
            "UPDATE connector_sync_failures "
            "SET error_message = '' "
            "WHERE error_message IS NULL"
        )
    )
    op.execute(sa.text("UPDATE connector_sync_failures SET created_at = COALESCE(created_at, now())"))
    op.execute(sa.text("ALTER TABLE connector_sync_failures ALTER COLUMN created_at SET DEFAULT now()"))
    op.execute(sa.text("ALTER TABLE connector_sync_failures ALTER COLUMN created_at SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE connector_sync_failures ALTER COLUMN failure_stage SET NOT NULL"))
    op.execute(sa.text("ALTER TABLE connector_sync_failures ALTER COLUMN error_message SET NOT NULL"))

    inspector = sa.inspect(op.get_bind())
    _drop_index_if_exists(inspector, "connector_sync_failures", "idx_connector_sync_failures_unresolved")
    _ensure_index(inspector, "connector_sync_failures", "ix_connector_sync_failures_tenant_id", ["tenant_id"])
    _ensure_index(inspector, "connector_sync_failures", "ix_connector_sync_failures_repository_id", ["repository_id"])
    _ensure_index(inspector, "connector_sync_failures", "ix_connector_sync_failures_sync_run_id", ["sync_run_id"])
    _ensure_index(inspector, "connector_sync_failures", "ix_connector_sync_failures_connector_file_id", ["connector_file_id"])
    _ensure_index(inspector, "connector_sync_failures", "ix_connector_sync_failures_resolved", ["resolved"])
    _ensure_foreign_key(
        inspector,
        "connector_sync_failures",
        "fk_connector_sync_failures_tenant_id",
        "tenants",
        ["tenant_id"],
        ["tenant_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_sync_failures",
        "fk_connector_sync_failures_repository_id",
        "repositories",
        ["repository_id"],
        ["repository_id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_sync_failures",
        "fk_connector_sync_failures_sync_run_id",
        "connector_sync_runs",
        ["sync_run_id"],
        ["id"],
    )
    _ensure_foreign_key(
        inspector,
        "connector_sync_failures",
        "fk_connector_sync_failures_connector_file_id",
        "connector_files",
        ["connector_file_id"],
        ["id"],
    )


def _reconcile_repository_columns(inspector) -> None:
    _ensure_column(inspector, "repositories", sa.Column("connection_config", sa.JSON(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("sync_status", sa.String(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_run_id", sa.String(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_status", sa.String(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_started_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_completed_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("last_sync_error", sa.Text(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("sync_enabled", sa.Boolean(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("sync_interval_minutes", sa.Integer(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("sync_cursor", sa.Text(), nullable=True))
    _ensure_column(inspector, "repositories", sa.Column("sync_metadata", sa.JSON(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    _alter_column_to_varchar(inspector, "repositories", "last_sync_run_id")
    for column_name in ("last_sync_at", "last_sync_started_at", "last_sync_completed_at"):
        _alter_column_to_timestamptz(inspector, "repositories", column_name)
    _ensure_json_column_type(sa.inspect(op.get_bind()), "repositories", "sync_metadata")
    _ensure_json_column_type(sa.inspect(op.get_bind()), "repositories", "connection_config")

    inspector = sa.inspect(op.get_bind())
    connection_config_default = _empty_json_literal(inspector, "repositories", "connection_config")
    sync_metadata_default = _empty_json_literal(inspector, "repositories", "sync_metadata")
    op.execute(sa.text(f"UPDATE repositories SET connection_config = {connection_config_default} WHERE connection_config IS NULL"))
    op.execute(sa.text("UPDATE repositories SET sync_status = 'NOT_SYNCED' WHERE sync_status IS NULL"))
    op.execute(sa.text(f"UPDATE repositories SET sync_metadata = {sync_metadata_default} WHERE sync_metadata IS NULL"))
    op.execute(sa.text("UPDATE repositories SET sync_enabled = true WHERE sync_enabled IS NULL"))
    op.execute(sa.text(f"ALTER TABLE repositories ALTER COLUMN connection_config SET DEFAULT {connection_config_default}"))
    op.execute(sa.text("ALTER TABLE repositories ALTER COLUMN sync_status SET DEFAULT 'NOT_SYNCED'"))
    op.execute(sa.text(f"ALTER TABLE repositories ALTER COLUMN sync_metadata SET DEFAULT {sync_metadata_default}"))
    op.execute(sa.text("ALTER TABLE repositories ALTER COLUMN sync_enabled SET DEFAULT true"))


def _reconcile_document_connector_columns(inspector) -> None:
    _ensure_column(inspector, "documents", sa.Column("source_type", sa.String(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("external_file_id", sa.Text(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("file_hash", sa.Text(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("version_number", sa.Integer(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("is_current_version", sa.Boolean(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("is_deleted", sa.Boolean(), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    _ensure_column(inspector, "documents", sa.Column("connector_file_id", sa.String(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    _alter_column_to_varchar(inspector, "documents", "connector_file_id")
    _alter_column_to_timestamptz(inspector, "documents", "source_created_at")
    _alter_column_to_timestamptz(inspector, "documents", "source_modified_at")
    _alter_column_to_timestamptz(inspector, "documents", "deleted_at")

    _ensure_default_and_not_null("documents", "version_number", "1")
    _ensure_default_and_not_null("documents", "is_current_version", "true")
    _ensure_default_and_not_null("documents", "is_deleted", "false")

    inspector = sa.inspect(op.get_bind())
    _ensure_index(inspector, "documents", "ix_documents_connector_file_id", ["connector_file_id"])
    _ensure_index(inspector, "documents", "ix_documents_external_file_id", ["external_file_id"])
    _ensure_index(inspector, "documents", "ix_documents_file_hash", ["file_hash"])
    _ensure_index(inspector, "documents", "ix_documents_is_deleted", ["is_deleted"])
    _ensure_index(inspector, "documents", "ix_documents_source_type", ["source_type"])


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _reconcile_repository_columns(inspector)

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "connector_sync_runs"):
        _create_connector_sync_runs()
    else:
        _reconcile_connector_sync_runs(inspector)

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "connector_files"):
        _create_connector_files()
    else:
        _reconcile_connector_files(inspector)

    inspector = sa.inspect(bind)
    if not _table_exists(inspector, "connector_sync_failures"):
        _create_connector_sync_failures()
    else:
        _reconcile_connector_sync_failures(inspector)

    inspector = sa.inspect(bind)
    _reconcile_document_connector_columns(inspector)


def downgrade() -> None:
    raise NotImplementedError(
        "This reconciliation migration is intentionally one-way. "
        "Restore from backup if rollback is required."
    )
