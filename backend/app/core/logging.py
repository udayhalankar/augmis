from __future__ import annotations

import logging
import traceback
from threading import Lock
from typing import Any

from app.core.request_context import get_request_context
from app.services.server_log_service import create_server_log


_WRITE_LOCK = Lock()


class RuntimeDatabaseLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        if not (record.name.startswith("app.") or record.name.startswith("init_db")):
            return

        context = get_request_context()
        metadata: dict[str, Any] = {}
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            metadata.update(record.metadata)

        extra_context = getattr(record, "context", None)
        if isinstance(extra_context, dict):
            context = {
                **context,
                **{key: value for key, value in extra_context.items() if value is not None},
            }

        exception_text = None
        if record.exc_info:
            exception_text = "".join(traceback.format_exception(*record.exc_info))

        with _WRITE_LOCK:
            try:
                create_server_log(
                    source=str(getattr(record, "source", "backend") or "backend"),
                    level=record.levelname,
                    logger=record.name,
                    category=getattr(record, "category", None),
                    message=record.getMessage(),
                    exception=exception_text,
                    route=context.get("route"),
                    method=context.get("method"),
                    status_code=context.get("status_code"),
                    request_id=context.get("request_id"),
                    tenant_id=context.get("tenant_id"),
                    user_id=context.get("user_id"),
                    user_email=context.get("user_email"),
                    repository_id=context.get("repository_id"),
                    business_area=context.get("business_area"),
                    component=getattr(record, "component", None) or context.get("component"),
                    is_critical=bool(getattr(record, "is_critical", False) or record.levelno >= logging.ERROR),
                    metadata=metadata,
                )
            except Exception:
                # Logging persistence should never crash request handling.
                return


def configure_application_logging() -> None:
    root_logger = logging.getLogger()
    if any(
        getattr(handler, "_augmis_runtime_handler", False)
        for handler in root_logger.handlers
    ):
        return

    handler = RuntimeDatabaseLogHandler()
    handler.setLevel(logging.INFO)
    handler._augmis_runtime_handler = True  # type: ignore[attr-defined]

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
