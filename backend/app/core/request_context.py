from __future__ import annotations

from contextvars import ContextVar
from typing import Any


_REQUEST_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})


def set_request_context(**values: Any):
    return _REQUEST_CONTEXT.set({k: v for k, v in values.items() if v is not None})


def update_request_context(**values: Any) -> dict[str, Any]:
    current = dict(_REQUEST_CONTEXT.get({}))
    for key, value in values.items():
        if value is not None:
            current[key] = value
    _REQUEST_CONTEXT.set(current)
    return current


def get_request_context() -> dict[str, Any]:
    return dict(_REQUEST_CONTEXT.get({}))


def clear_request_context(token=None) -> None:
    if token is not None:
        _REQUEST_CONTEXT.reset(token)
        return

    _REQUEST_CONTEXT.set({})
