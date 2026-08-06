"""post-reconciliation check

Revision ID: 9af781b967f6
Revises: 88fa7488037f
Create Date: 2026-06-09 17:20:12.761043
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9af781b967f6"
down_revision: Union[str, Sequence[str], None] = "88fa7488037f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AUDITED_TABLES = [
    "tenants",
    "plans",
    "tenant_usage",
    "users",
    "repositories",
    "repository_access",
    "documents",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "audit_logs",
    "connector_sync_runs",
    "connector_files",
    "connector_sync_failures",
]

TABLES_WITH_PREEXISTING_CREATED_AT = {
    "tenants",
    "users",
    "repositories",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "audit_logs",
    "connector_sync_runs",
    "connector_files",
    "connector_sync_failures",
}


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_column(inspector, table_name: str, column: sa.Column) -> None:
    if column.name not in _column_names(inspector, table_name):
        op.add_column(table_name, column)


def _backfill_created_by(table_name: str, columns: set[str]) -> None:
    if "created_by" not in columns:
        return

    if table_name == "documents" and "uploaded_by" in columns:
        op.execute(
            sa.text(
                'UPDATE "documents" '
                'SET "created_by" = "uploaded_by" '
                'WHERE "created_by" IS NULL AND "uploaded_by" IS NOT NULL'
            )
        )
    elif table_name == "chat_sessions" and "user_id" in columns:
        op.execute(
            sa.text(
                'UPDATE "chat_sessions" '
                'SET "created_by" = "user_id" '
                'WHERE "created_by" IS NULL AND "user_id" IS NOT NULL'
            )
        )
    elif table_name == "chat_messages" and "user_id" in columns:
        op.execute(
            sa.text(
                'UPDATE "chat_messages" '
                'SET "created_by" = "user_id" '
                'WHERE "created_by" IS NULL AND "user_id" IS NOT NULL'
            )
        )
    elif table_name == "audit_logs" and "user_id" in columns:
        op.execute(
            sa.text(
                'UPDATE "audit_logs" '
                'SET "created_by" = "user_id" '
                'WHERE "created_by" IS NULL AND "user_id" IS NOT NULL'
            )
        )
    elif table_name == "connector_sync_runs" and "started_by" in columns:
        op.execute(
            sa.text(
                'UPDATE "connector_sync_runs" '
                'SET "created_by" = "started_by" '
                'WHERE "created_by" IS NULL AND "started_by" IS NOT NULL'
            )
        )


def _created_at_fallback(table_name: str, columns: set[str]) -> str:
    if table_name == "documents" and "uploaded_at" in columns:
        return 'COALESCE("created_at", "uploaded_at", now())'
    return 'COALESCE("created_at", now())'


def _modified_at_fallback(table_name: str, columns: set[str]) -> str:
    candidates = ['"modified_at"']

    if "updated_at" in columns:
        candidates.append('"updated_at"')

    if table_name == "documents" and "uploaded_at" in columns:
        candidates.append('"uploaded_at"')

    if "created_at" in columns:
        candidates.append('"created_at"')

    candidates.append("now()")
    return f"COALESCE({', '.join(candidates)})"


def _reconcile_audit_columns(table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, table_name):
        return

    _ensure_column(inspector, table_name, sa.Column("created_by", sa.String(), nullable=True))
    _ensure_column(
        inspector,
        table_name,
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    _ensure_column(inspector, table_name, sa.Column("modified_by", sa.String(), nullable=True))
    _ensure_column(
        inspector,
        table_name,
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
    )

    inspector = sa.inspect(bind)
    columns = _column_names(inspector, table_name)

    _backfill_created_by(table_name, columns)

    if "created_by" in columns and "modified_by" in columns:
        op.execute(
            sa.text(
                f'UPDATE "{table_name}" '
                'SET "modified_by" = "created_by" '
                'WHERE "modified_by" IS NULL AND "created_by" IS NOT NULL'
            )
        )

    if "created_at" in columns:
        op.execute(
            sa.text(
                f'UPDATE "{table_name}" '
                f'SET "created_at" = {_created_at_fallback(table_name, columns)} '
                'WHERE "created_at" IS NULL'
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "created_at" SET DEFAULT now()'
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "created_at" SET NOT NULL'
            )
        )

    if "modified_at" in columns:
        op.execute(
            sa.text(
                f'UPDATE "{table_name}" '
                f'SET "modified_at" = {_modified_at_fallback(table_name, columns)} '
                'WHERE "modified_at" IS NULL'
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "modified_at" SET DEFAULT now()'
            )
        )
        op.execute(
            sa.text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "modified_at" SET NOT NULL'
            )
        )


def upgrade() -> None:
    for table_name in AUDITED_TABLES:
        _reconcile_audit_columns(table_name)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in reversed(AUDITED_TABLES):
        if not _table_exists(inspector, table_name):
            continue

        columns = _column_names(inspector, table_name)

        if "modified_at" in columns:
            op.drop_column(table_name, "modified_at")
        if "modified_by" in columns:
            op.drop_column(table_name, "modified_by")
        if table_name != "repositories" and "created_by" in columns:
            op.drop_column(table_name, "created_by")
        if table_name not in TABLES_WITH_PREEXISTING_CREATED_AT and "created_at" in columns:
            op.drop_column(table_name, "created_at")

        inspector = sa.inspect(bind)
