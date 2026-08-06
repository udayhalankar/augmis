from __future__ import annotations

from uuid import uuid4
import logging

from fastapi import Request

from app.core.request_context import clear_request_context, set_request_context, update_request_context


logger = logging.getLogger(__name__)


async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or f"REQ-{str(uuid4())[:12].upper()}"
    token = set_request_context(
        request_id=request_id,
        route=request.url.path,
        method=request.method,
        client_ip=request.client.host if request.client else None,
    )
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        update_request_context(status_code=response.status_code)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception(
            "Unhandled request exception",
            extra={"category": "request_error", "is_critical": True},
        )
        raise
    finally:
        clear_request_context(token)
