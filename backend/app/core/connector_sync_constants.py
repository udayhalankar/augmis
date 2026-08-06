class ConnectorSyncStatus:
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConnectorFileStatus:
    PENDING = "pending"
    NEW = "new"
    UNCHANGED = "unchanged"
    UPDATED = "updated"
    INDEXED = "indexed"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FAILED = "failed"
    DELETED = "deleted"


class ConnectorSyncMode:
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    RETRY = "retry"


class ConnectorFailureStage:
    DISCOVERY = "discovery"
    DOWNLOAD = "download"
    HASH = "hash"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    DB_WRITE = "db_write"
    DELETE = "delete"


class ConnectorRetryStatus:
    READY = "ready"
    WAITING = "waiting"
    MAX_RETRIES_REACHED = "max_retries_reached"
