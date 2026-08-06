from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.agent_models import (
    AgentCommandPollRequest,
    AgentCommandResultRequest,
    AgentHeartbeatRequest,
    AgentRegistrationRequest,
    AgentSyncRequest,
)
from app.services.agent_service import (
    list_agents,
    pull_symployee_commands,
    record_heartbeat,
    record_sync,
    record_symployee_command_result,
    register_agent,
)


router = APIRouter(prefix="/api/agents", tags=["Migration Agents"])


@router.post("/register")
def register_migration_agent(
    payload: AgentRegistrationRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": register_agent(db, payload),
    }


@router.post("/heartbeat")
def heartbeat_migration_agent(
    payload: AgentHeartbeatRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": record_heartbeat(db, payload),
    }


@router.post("/sync")
def sync_migration_agent(
    payload: AgentSyncRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": record_sync(db, payload),
    }


@router.post("/changes")
def changes_migration_agent(
    payload: AgentSyncRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": record_sync(db, payload),
    }


@router.post("/commands/pull")
def pull_agent_commands(
    payload: AgentCommandPollRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": pull_symployee_commands(db, payload),
    }


@router.post("/commands/result")
def post_agent_command_result(
    payload: AgentCommandResultRequest,
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": record_symployee_command_result(db, payload),
    }


@router.get("")
def get_migration_agents(
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_role(["SUPER_ADMIN"])),
    db: Session = Depends(get_db),
):
    return {
        "success": True,
        "data": list_agents(db, limit=limit),
    }
