from sqlalchemy import text

from app import db_models  # noqa: F401
from app.core.database import Base, engine


SCHEMA_PATCHES = [
    "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS connection_config JSON DEFAULT '{}'::json",
    "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS sync_status VARCHAR DEFAULT 'NOT_SYNCED'",
    "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ NULL",
    "UPDATE repositories SET connection_config = '{}'::json WHERE connection_config IS NULL",
    "UPDATE repositories SET sync_status = 'NOT_SYNCED' WHERE sync_status IS NULL",
]

RUNTIME_STATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS runtime_auth_state (
        state_name VARCHAR PRIMARY KEY,
        state_json JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS runtime_auth_challenges (
        store_name VARCHAR PRIMARY KEY,
        store_json JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
]

AUDITED_TABLES = [
    "tenants",
    "plans",
    "tenant_usage",
    "users",
    "auth_sessions",
    "intelligence_patterns",
    "business_areas",
    "extracted_facts",
    "repositories",
    "repository_access",
    "documents",
    "document_chunks",
    "chat_sessions",
    "chat_messages",
    "audit_logs",
    "server_logs",
    "connector_sync_runs",
    "connector_files",
    "connector_sync_failures",
]


def apply_audit_schema_patches(connection):
    for table_name in AUDITED_TABLES:
        connection.execute(
            text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS created_by VARCHAR')
        )
        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()'
            )
        )
        connection.execute(
            text(f'ALTER TABLE "{table_name}" ADD COLUMN IF NOT EXISTS modified_by VARCHAR')
        )
        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ADD COLUMN IF NOT EXISTS modified_at TIMESTAMPTZ DEFAULT now()'
            )
        )

        if table_name == "documents":
            connection.execute(
                text(
                    'UPDATE "documents" '
                    'SET "created_by" = "uploaded_by" '
                    'WHERE "created_by" IS NULL AND "uploaded_by" IS NOT NULL'
                )
            )
        elif table_name in {"chat_sessions", "chat_messages", "audit_logs", "server_logs"}:
            connection.execute(
                text(
                    f'UPDATE "{table_name}" '
                    'SET "created_by" = "user_id" '
                    'WHERE "created_by" IS NULL AND "user_id" IS NOT NULL'
                )
            )
        elif table_name == "connector_sync_runs":
            connection.execute(
                text(
                    'UPDATE "connector_sync_runs" '
                    'SET "created_by" = "started_by" '
                    'WHERE "created_by" IS NULL AND "started_by" IS NOT NULL'
                )
            )

        connection.execute(
            text(
                f'UPDATE "{table_name}" '
                'SET "modified_by" = "created_by" '
                'WHERE "modified_by" IS NULL AND "created_by" IS NOT NULL'
            )
        )

        if table_name == "documents":
            connection.execute(
                text(
                    'UPDATE "documents" '
                    'SET "created_at" = COALESCE("created_at", "uploaded_at", now()) '
                    'WHERE "created_at" IS NULL'
                )
            )
            connection.execute(
                text(
                    'UPDATE "documents" '
                    'SET "modified_at" = COALESCE("modified_at", "created_at", "uploaded_at", now()) '
                    'WHERE "modified_at" IS NULL'
                )
            )
        else:
            connection.execute(
                text(
                    f'UPDATE "{table_name}" '
                    'SET "created_at" = COALESCE("created_at", now()) '
                    'WHERE "created_at" IS NULL'
                )
            )
            modified_expr = 'COALESCE("modified_at", '
            if table_name == "connector_files":
                modified_expr += '"updated_at", '
            elif table_name == "chat_sessions":
                modified_expr += '"updated_at", '
            modified_expr += '"created_at", now())'
            connection.execute(
                text(
                    f'UPDATE "{table_name}" '
                    f'SET "modified_at" = {modified_expr} '
                    'WHERE "modified_at" IS NULL'
                )
            )

        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "created_at" SET DEFAULT now()'
            )
        )
        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "created_at" SET NOT NULL'
            )
        )
        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "modified_at" SET DEFAULT now()'
            )
        )
        connection.execute(
            text(
                f'ALTER TABLE "{table_name}" '
                'ALTER COLUMN "modified_at" SET NOT NULL'
            )
        )


def init_db():
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        for statement in RUNTIME_STATE_TABLES:
            connection.execute(text(statement))
        connection.execute(
            text('ALTER TABLE "audit_logs" ADD COLUMN IF NOT EXISTS request_id VARCHAR')
        )
        for statement in SCHEMA_PATCHES:
            connection.execute(text(statement))
        apply_audit_schema_patches(connection)

    print("Database tables created successfully.")


    #added by UH for testing purposes, to be removed later
def main():
    init_db()

if __name__ == "__main__":
    main()

    #added by UH for testing purposes, to be removed later
