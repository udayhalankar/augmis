import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.database import engine
from app.core.config import settings
from app.core.request_context import update_request_context
from app.core.security import get_current_user, require_role
from app.models.platform_models import FrontendLogCreateRequest, PlatformConfigUpdateRequest
from app.services.audit_service import create_audit_log
from app.services.platform_settings_service import (
    get_platform_settings_snapshot,
    update_platform_settings,
)
from app.services.server_log_service import (
    append_frontend_log,
    export_server_logs_csv,
    list_server_logs,
    mark_server_log_critical,
)


router = APIRouter(prefix="/api/platform", tags=["Platform"])
logger = logging.getLogger(__name__)


@router.get("/config")
def get_platform_config(
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    return {
        "success": True,
        "data": get_platform_settings_snapshot(),
    }


@router.patch("/config")
def patch_platform_config(
    payload: PlatformConfigUpdateRequest,
    request: Request,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
    db: Session = Depends(get_db),
):
    raw_payload = payload.model_dump(exclude_none=True)
    try:
        updated = update_platform_settings(raw_payload)
    except ValueError as exc:
        detail = str(exc)
        try:
            parsed = json.loads(detail)
            raise HTTPException(status_code=400, detail=parsed) from exc
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail=detail) from exc

    create_audit_log(
        db=db,
        tenant_id=current_user["tenant_id"],
        user_id=current_user["user_id"],
        event_type="PLATFORM_CONFIG_UPDATED",
        event_category="SETTINGS",
        description="AUGMIS platform configuration updated",
        resource_type="platform_config",
        resource_id="runtime_platform_settings",
        request=request,
        metadata={
            "updated_keys": sorted(raw_payload.keys()),
            "restart_required": updated.get("restart_required", False),
        },
    )

    return {
        "success": True,
        "data": updated,
    }


@router.post("/test/openai")
def test_openai_config(
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    if not str(settings.OPENAI_API_KEY or "").strip():
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured.")

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        chat_response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": "health check"}],
            max_tokens=1,
            temperature=0,
        )
        embedding_response = client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=["health check"],
        )
        return {
            "success": True,
            "data": {
                "chat_model": settings.OPENAI_MODEL,
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                "chat_test": bool(chat_response.choices),
                "embedding_test": bool(embedding_response.data),
                "message": "OpenAI chat and embedding checks completed successfully.",
            },
        }
    except Exception as exc:
        logger.exception(
            "OpenAI health check failed",
            extra={"category": "openai_health_check", "is_critical": True},
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/test/database")
def test_database_config(
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            vector_enabled = bool(
                connection.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                ).scalar()
            )
        return {
            "success": True,
            "data": {
                "driver": engine.url.drivername,
                "host": engine.url.host,
                "database": engine.url.database,
                "pgvector_enabled": vector_enabled,
                "message": "Database connectivity check completed successfully.",
            },
        }
    except Exception as exc:
        logger.exception(
            "Database health check failed",
            extra={"category": "database_health_check", "is_critical": True},
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/server-logs")
def get_server_logs(
    source: str | None = Query(None),
    level: str | None = Query(None),
    q: str | None = Query(None),
    route: str | None = Query(None),
    user: str | None = Query(None),
    repository_id: str | None = Query(None),
    business_area: str | None = Query(None),
    request_id: str | None = Query(None),
    category: str | None = Query(None),
    critical_only: bool = Query(False),
    start_at: str | None = Query(None),
    end_at: str | None = Query(None),
    limit: int = 200,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    logs = list_server_logs(
        source=source,
        level=level,
        q=q,
        route=route,
        user=user,
        repository_id=repository_id,
        business_area=business_area,
        request_id=request_id,
        category=category,
        critical_only=critical_only,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )
    return {
        "success": True,
        "data": logs,
    }


@router.get("/server-logs/export")
def export_server_logs(
    source: str | None = Query(None),
    level: str | None = Query(None),
    q: str | None = Query(None),
    route: str | None = Query(None),
    user: str | None = Query(None),
    repository_id: str | None = Query(None),
    business_area: str | None = Query(None),
    request_id: str | None = Query(None),
    category: str | None = Query(None),
    critical_only: bool = Query(False),
    start_at: str | None = Query(None),
    end_at: str | None = Query(None),
    limit: int = 1000,
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    logs = list_server_logs(
        source=source,
        level=level,
        q=q,
        route=route,
        user=user,
        repository_id=repository_id,
        business_area=business_area,
        request_id=request_id,
        category=category,
        critical_only=critical_only,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )
    csv_content = export_server_logs_csv(logs)
    return PlainTextResponse(
        csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=augmis-server-logs.csv"},
    )


@router.patch("/server-logs/{log_id}/critical")
def set_server_log_critical(
    log_id: str,
    is_critical: bool = Query(...),
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
):
    updated = mark_server_log_critical(log_id, is_critical)
    if not updated:
        raise HTTPException(status_code=404, detail="Server log not found")
    return {"success": True, "data": updated}


@router.post("/frontend-logs")
def ingest_frontend_log(
    payload: FrontendLogCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    update_request_context(
        tenant_id=current_user.get("tenant_id"),
        user_id=current_user.get("user_id"),
        user_email=current_user.get("email"),
        route=payload.route or request.url.path,
        method=payload.method,
        request_id=payload.request_id or getattr(request.state, "request_id", None),
        repository_id=payload.repository_id,
        business_area=payload.business_area,
        component=payload.component,
        status_code=payload.status_code,
    )
    created = append_frontend_log(
        {
            "message": payload.message,
            "level": payload.level,
            "category": payload.category,
            "route": payload.route,
            "method": payload.method,
            "status_code": payload.status_code,
            "request_id": payload.request_id or getattr(request.state, "request_id", None),
            "stack": payload.stack,
            "user_agent": payload.user_agent or request.headers.get("user-agent"),
            "tenant_id": current_user.get("tenant_id"),
            "user_id": current_user.get("user_id"),
            "user_email": current_user.get("email"),
            "repository_id": payload.repository_id,
            "business_area": payload.business_area,
            "component": payload.component,
            "is_critical": payload.is_critical,
            "metadata": payload.metadata or {},
        }
    )
    return {
        "success": True,
        "data": created,
    }
