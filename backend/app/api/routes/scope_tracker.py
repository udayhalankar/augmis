from fastapi import APIRouter, Depends, Query

from app.core.security import require_saas_access
from app.models.scope_models import (
    ItemCreateRequest,
    ItemUpdateRequest,
    MilestoneCreateRequest,
    MilestoneUpdateRequest,
    PhaseCreateRequest,
    PhaseUpdateRequest,
)
from app.services.scope_service import (
    create_item,
    create_milestone,
    create_phase,
    delete_item,
    delete_milestone,
    delete_phase,
    get_scope_tracker,
    update_item,
    update_milestone,
    update_phase,
)


router = APIRouter(prefix="/api/scope-tracker", tags=["Scope Tracker"])


@router.get("")
def scope_tracker(
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return get_scope_tracker()


@router.post("/phases")
def add_phase(
    payload: PhaseCreateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return create_phase(payload, track=track)


@router.patch("/phases/{phase_id}")
def edit_phase(
    phase_id: str,
    payload: PhaseUpdateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return update_phase(phase_id, payload, track=track)


@router.delete("/phases/{phase_id}")
def remove_phase(
    phase_id: str,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return delete_phase(phase_id, track=track)


@router.post("/phases/{phase_id}/milestones")
def add_milestone(
    phase_id: str,
    payload: MilestoneCreateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return create_milestone(phase_id, payload, track=track)


@router.patch("/phases/{phase_id}/milestones/{milestone_id}")
def edit_milestone(
    phase_id: str,
    milestone_id: str,
    payload: MilestoneUpdateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return update_milestone(phase_id, milestone_id, payload, track=track)


@router.delete("/phases/{phase_id}/milestones/{milestone_id}")
def remove_milestone(
    phase_id: str,
    milestone_id: str,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return delete_milestone(phase_id, milestone_id, track=track)


@router.post("/phases/{phase_id}/milestones/{milestone_id}/items")
def add_item(
    phase_id: str,
    milestone_id: str,
    payload: ItemCreateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return create_item(phase_id, milestone_id, payload, track=track)


@router.patch("/phases/{phase_id}/milestones/{milestone_id}/items/{item_id}")
def edit_item(
    phase_id: str,
    milestone_id: str,
    item_id: str,
    payload: ItemUpdateRequest,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return update_item(phase_id, milestone_id, item_id, payload, track=track)


@router.delete("/phases/{phase_id}/milestones/{milestone_id}/items/{item_id}")
def remove_item(
    phase_id: str,
    milestone_id: str,
    item_id: str,
    track: str = Query("augmis"),
    current_user: dict = Depends(require_saas_access("settings", "admin:settings")),
):
    return delete_item(phase_id, milestone_id, item_id, track=track)
