from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session

from app.db_models import SymployeeDocumentIdentity, SymployeeDocumentVersion
from app.services.symployee_lifecycle_service import apply_state_transition


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{str(uuid4())[:12].upper()}"


def _table(db: Session, table_name: str) -> Table:
    return Table(
        table_name,
        MetaData(),
        autoload_with=db.get_bind(),
    )


def _serialize_row(row) -> dict:
    return {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else value
        )
        for key, value in row._mapping.items()
    }


def _require_identity(db: Session, tenant_id: str, identity_id: str) -> SymployeeDocumentIdentity:
    identity = (
        db.query(SymployeeDocumentIdentity)
        .filter(
            SymployeeDocumentIdentity.tenant_id == tenant_id,
            SymployeeDocumentIdentity.identity_id == identity_id,
        )
        .first()
    )
    if not identity:
        raise ValueError("Document identity not found")
    return identity


def _require_version(
    db: Session,
    tenant_id: str,
    *,
    identity_id: str,
    version_id: str | None,
) -> SymployeeDocumentVersion | None:
    if not version_id:
        return None
    version = (
        db.query(SymployeeDocumentVersion)
        .filter(
            SymployeeDocumentVersion.tenant_id == tenant_id,
            SymployeeDocumentVersion.identity_id == identity_id,
            SymployeeDocumentVersion.version_id == version_id,
        )
        .first()
    )
    if not version:
        raise ValueError("Document version not found")
    return version


def _require_transmittal(db: Session, tenant_id: str, transmittal_id: str):
    transmittals = _table(db, "symployee_transmittals")
    row = db.execute(
        transmittals.select().where(
            transmittals.c.tenant_id == tenant_id,
            transmittals.c.transmittal_id == transmittal_id,
        )
    ).fetchone()
    if not row:
        raise ValueError("Transmittal not found")
    return row


def _find_transmittal_item(
    db: Session,
    tenant_id: str,
    *,
    transmittal_id: str,
    identity_id: str,
    version_id: str | None,
):
    items = _table(db, "symployee_transmittal_items")
    return db.execute(
        items.select().where(
            items.c.tenant_id == tenant_id,
            items.c.transmittal_id == transmittal_id,
            items.c.identity_id == identity_id,
            items.c.version_id == version_id,
        )
    ).fetchone()


def _derive_issue_status(direction: str, response_required: bool) -> str:
    normalized_direction = (direction or "").upper()
    if normalized_direction == "OUTGOING":
        return "AWAITING_ACKNOWLEDGEMENT" if response_required else "ISSUED"
    return "RECEIVED"


def _derive_issue_status_from_ack(status: str, response_status: str | None) -> str:
    normalized_status = (status or "").upper()
    normalized_response = (response_status or "").upper()
    if normalized_response in {"RESPONDED", "COMPLETED", "CLOSED"}:
        return "RESPONDED"
    if normalized_status in {"ACKNOWLEDGED", "RECEIVED", "ACCEPTED"}:
        return "ACKNOWLEDGED"
    if normalized_status == "OVERDUE":
        return "RESPONSE_OVERDUE"
    return "AWAITING_ACKNOWLEDGEMENT"


def _apply_issue_status(
    db: Session,
    tenant_id: str,
    *,
    identity: SymployeeDocumentIdentity,
    version: SymployeeDocumentVersion | None,
    transmittal_id: str,
    transmittal_item_id: str | None,
    new_state: str,
    event_type: str,
    performed_by: str | None,
    reason: str = "",
    metadata_json: dict | None = None,
) -> list[str]:
    event_ids: list[str] = []
    payload = {
        "transmittal_id": transmittal_id,
        "transmittal_item_id": transmittal_item_id,
        **(metadata_json or {}),
    }

    if identity.issue_status != new_state:
        transition = apply_state_transition(
            db,
            tenant_id,
            identity_id=identity.identity_id,
            version_id=None,
            state_dimension="issue_status",
            new_state=new_state,
            event_type=event_type,
            performed_by=performed_by,
            reason=reason,
            metadata_json=payload,
        )
        event_ids.append(transition["event_id"])

    if version and version.issue_status != new_state:
        transition = apply_state_transition(
            db,
            tenant_id,
            identity_id=identity.identity_id,
            version_id=version.version_id,
            state_dimension="issue_status",
            new_state=new_state,
            event_type=event_type,
            performed_by=performed_by,
            reason=reason,
            metadata_json=payload,
        )
        event_ids.append(transition["event_id"])

    return event_ids


def list_transmittals(
    db: Session,
    tenant_id: str,
    *,
    direction: str | None = None,
    limit: int = 100,
) -> dict:
    transmittals = _table(db, "symployee_transmittals")
    query = (
        transmittals.select()
        .where(transmittals.c.tenant_id == tenant_id)
        .order_by(transmittals.c.created_at.desc(), transmittals.c.transmittal_number.desc())
        .limit(max(1, min(limit, 500)))
    )
    if direction:
        query = query.where(transmittals.c.direction == direction)

    rows = db.execute(query).fetchall()
    return {
        "items": [_serialize_row(row) for row in rows],
        "filters": {
            "tenant_id": tenant_id,
            "direction": direction,
            "limit": max(1, min(limit, 500)),
        },
    }


def create_transmittal(
    db: Session,
    tenant_id: str,
    *,
    direction: str,
    purpose_code: str,
    sender_org: str | None = None,
    recipient_org: str | None = None,
    response_required: bool = False,
    response_due_at: datetime | None = None,
    prepared_by: str | None = None,
    workflow_instance_id: str | None = None,
    subject: str | None = None,
    notes: str | None = None,
    transmittal_number: str | None = None,
    metadata_json: dict | None = None,
) -> dict:
    transmittals = _table(db, "symployee_transmittals")
    generated_number = transmittal_number or f"TRM-{_now().strftime('%Y%m%d%H%M%S')}-{str(uuid4())[:4].upper()}"
    transmittal_id = _new_id("STM")
    db.execute(
        transmittals.insert().values(
            transmittal_id=transmittal_id,
            tenant_id=tenant_id,
            transmittal_number=generated_number,
            direction=direction,
            purpose_code=purpose_code,
            transmittal_status="DRAFT",
            sender_org=sender_org,
            recipient_org=recipient_org,
            response_required=response_required,
            response_due_at=response_due_at,
            prepared_by=prepared_by,
            workflow_instance_id=workflow_instance_id,
            subject=subject,
            notes=notes,
            metadata_json=metadata_json or {},
            created_by=prepared_by,
            created_at=_now(),
            modified_by=prepared_by,
            modified_at=_now(),
        )
    )
    db.commit()
    return {
        "transmittal_id": transmittal_id,
        "transmittal_number": generated_number,
        "direction": direction,
        "purpose_code": purpose_code,
        "transmittal_status": "DRAFT",
        "response_required": response_required,
        "response_due_at": response_due_at.isoformat() if response_due_at else None,
    }


def create_transmittal_item(
    db: Session,
    tenant_id: str,
    *,
    transmittal_id: str,
    identity_id: str,
    version_id: str | None = None,
    sequence_no: int = 1,
    purpose_code: str | None = None,
    response_code: str | None = None,
    created_by: str | None = None,
    metadata_json: dict | None = None,
) -> dict:
    transmittal = _require_transmittal(db, tenant_id, transmittal_id)
    identity = _require_identity(db, tenant_id, identity_id)
    version = _require_version(db, tenant_id, identity_id=identity_id, version_id=version_id)
    existing = _find_transmittal_item(
        db,
        tenant_id,
        transmittal_id=transmittal_id,
        identity_id=identity_id,
        version_id=version_id,
    )
    if existing:
        return {
            "transmittal_item_id": existing.transmittal_item_id,
            "item_status": existing.item_status,
            "issue_status": existing.issue_status,
            "existing": True,
        }

    issue_status = _derive_issue_status(transmittal.direction, bool(transmittal.response_required))
    item_id = _new_id("STI")
    event_ids = _apply_issue_status(
        db,
        tenant_id,
        identity=identity,
        version=version,
        transmittal_id=transmittal_id,
        transmittal_item_id=item_id,
        new_state=issue_status,
        event_type="TRANSMITTAL_ITEM_CREATED",
        performed_by=created_by,
        reason=f"Transmittal item created for {transmittal.transmittal_number}",
        metadata_json={
            "direction": transmittal.direction,
            "purpose_code": purpose_code or transmittal.purpose_code,
            **(metadata_json or {}),
        },
    )

    items = _table(db, "symployee_transmittal_items")
    db.execute(
        items.insert().values(
            transmittal_item_id=item_id,
            tenant_id=tenant_id,
            transmittal_id=transmittal_id,
            identity_id=identity_id,
            version_id=version_id,
            item_status="PENDING",
            issue_status=issue_status,
            sequence_no=sequence_no,
            document_number=identity.canonical_document_number,
            revision_code=version.revision_code if version else None,
            purpose_code=purpose_code or transmittal.purpose_code,
            response_code=response_code,
            metadata_json={
                "lifecycle_event_ids": event_ids,
                **(metadata_json or {}),
            },
            created_by=created_by,
            created_at=_now(),
            modified_by=created_by,
            modified_at=_now(),
        )
    )
    db.commit()
    return {
        "transmittal_item_id": item_id,
        "transmittal_id": transmittal_id,
        "identity_id": identity_id,
        "version_id": version_id,
        "item_status": "PENDING",
        "issue_status": issue_status,
        "lifecycle_event_ids": event_ids,
        "existing": False,
    }


def acknowledge_transmittal(
    db: Session,
    tenant_id: str,
    *,
    transmittal_id: str,
    recipient_ref: str,
    status: str,
    comments: str = "",
    transmittal_item_id: str | None = None,
    recipient_name: str | None = None,
    response_status: str | None = None,
    due_at: datetime | None = None,
    modified_by: str | None = None,
) -> dict:
    transmittal = _require_transmittal(db, tenant_id, transmittal_id)
    items = _table(db, "symployee_transmittal_items")
    acknowledgements = _table(db, "symployee_distribution_acknowledgements")

    item = None
    identity = None
    version = None
    if transmittal_item_id:
        item = db.execute(
            items.select().where(
                items.c.tenant_id == tenant_id,
                items.c.transmittal_item_id == transmittal_item_id,
                items.c.transmittal_id == transmittal_id,
            )
        ).fetchone()
        if not item:
            raise ValueError("Transmittal item not found")
        identity = _require_identity(db, tenant_id, item.identity_id)
        version = _require_version(db, tenant_id, identity_id=item.identity_id, version_id=item.version_id)

    existing = db.execute(
        acknowledgements.select().where(
            acknowledgements.c.tenant_id == tenant_id,
            acknowledgements.c.transmittal_id == transmittal_id,
            acknowledgements.c.transmittal_item_id == transmittal_item_id,
            acknowledgements.c.recipient_ref == recipient_ref,
        )
    ).fetchone()

    ack_status = status.upper()
    normalized_response_status = response_status.upper() if response_status else None
    acknowledgement_id = existing.acknowledgement_id if existing else _new_id("SDA")
    acknowledged_at = _now() if ack_status in {"ACKNOWLEDGED", "RECEIVED", "ACCEPTED"} else None
    responded_at = _now() if normalized_response_status in {"RESPONDED", "COMPLETED", "CLOSED"} else None
    response_due_at = due_at or transmittal.response_due_at

    if existing:
        db.execute(
            acknowledgements.update()
            .where(
                acknowledgements.c.tenant_id == tenant_id,
                acknowledgements.c.acknowledgement_id == acknowledgement_id,
            )
            .values(
                recipient_name=recipient_name or existing.recipient_name,
                acknowledgement_status=ack_status,
                response_status=normalized_response_status,
                due_at=response_due_at,
                acknowledged_at=acknowledged_at or existing.acknowledged_at,
                responded_at=responded_at or existing.responded_at,
                comments=comments or existing.comments,
                metadata_json=dict(existing.metadata_json or {}),
                modified_by=modified_by,
                modified_at=_now(),
            )
        )
    else:
        db.execute(
            acknowledgements.insert().values(
                acknowledgement_id=acknowledgement_id,
                tenant_id=tenant_id,
                transmittal_id=transmittal_id,
                transmittal_item_id=transmittal_item_id,
                recipient_ref=recipient_ref,
                recipient_name=recipient_name,
                acknowledgement_status=ack_status,
                response_status=normalized_response_status,
                due_at=response_due_at,
                acknowledged_at=acknowledged_at,
                responded_at=responded_at,
                comments=comments or None,
                metadata_json={},
                created_by=modified_by,
                created_at=_now(),
                modified_by=modified_by,
                modified_at=_now(),
            )
        )

    lifecycle_event_ids: list[str] = []
    issue_status = None
    if item and identity:
        issue_status = _derive_issue_status_from_ack(ack_status, normalized_response_status)
        lifecycle_event_ids = _apply_issue_status(
            db,
            tenant_id,
            identity=identity,
            version=version,
            transmittal_id=transmittal_id,
            transmittal_item_id=transmittal_item_id,
            new_state=issue_status,
            event_type="TRANSMITTAL_ACKNOWLEDGED",
            performed_by=modified_by,
            reason=comments,
            metadata_json={
                "recipient_ref": recipient_ref,
                "acknowledgement_status": ack_status,
                "response_status": normalized_response_status,
            },
        )
        db.execute(
            items.update()
            .where(
                items.c.tenant_id == tenant_id,
                items.c.transmittal_item_id == transmittal_item_id,
            )
            .values(
                item_status="ACKNOWLEDGED" if ack_status != "OVERDUE" else "OVERDUE",
                issue_status=issue_status,
                response_code=normalized_response_status or item.response_code,
                metadata_json={
                    **dict(item.metadata_json or {}),
                    "acknowledgement_id": acknowledgement_id,
                    "lifecycle_event_ids": lifecycle_event_ids,
                },
                modified_by=modified_by,
                modified_at=_now(),
            )
        )

    db.commit()
    return {
        "acknowledgement_id": acknowledgement_id,
        "transmittal_id": transmittal_id,
        "transmittal_item_id": transmittal_item_id,
        "recipient_ref": recipient_ref,
        "acknowledgement_status": ack_status,
        "response_status": normalized_response_status,
        "issue_status": issue_status,
        "lifecycle_event_ids": lifecycle_event_ids,
    }


def refresh_response_due_status(
    db: Session,
    tenant_id: str,
    *,
    transmittal_id: str | None = None,
) -> dict:
    acknowledgements = _table(db, "symployee_distribution_acknowledgements")
    items = _table(db, "symployee_transmittal_items")
    query = acknowledgements.select().where(
        acknowledgements.c.tenant_id == tenant_id,
        acknowledgements.c.due_at.is_not(None),
        acknowledgements.c.due_at < _now(),
        acknowledgements.c.acknowledgement_status.in_(["PENDING", "SENT", "DUE"]),
    )
    if transmittal_id:
        query = query.where(acknowledgements.c.transmittal_id == transmittal_id)

    rows = db.execute(query).fetchall()
    changed_items: list[str] = []

    for row in rows:
        db.execute(
            acknowledgements.update()
            .where(
                acknowledgements.c.tenant_id == tenant_id,
                acknowledgements.c.acknowledgement_id == row.acknowledgement_id,
            )
            .values(
                acknowledgement_status="OVERDUE",
                metadata_json={
                    **dict(row.metadata_json or {}),
                    "response_due_state": "OVERDUE",
                    "response_due_checked_at": _now().isoformat(),
                },
                modified_at=_now(),
            )
        )
        if row.transmittal_item_id:
            item = db.execute(
                items.select().where(
                    items.c.tenant_id == tenant_id,
                    items.c.transmittal_item_id == row.transmittal_item_id,
                )
            ).fetchone()
            if not item:
                continue
            identity = _require_identity(db, tenant_id, item.identity_id)
            version = _require_version(db, tenant_id, identity_id=item.identity_id, version_id=item.version_id)
            event_ids = _apply_issue_status(
                db,
                tenant_id,
                identity=identity,
                version=version,
                transmittal_id=row.transmittal_id,
                transmittal_item_id=row.transmittal_item_id,
                new_state="RESPONSE_OVERDUE",
                event_type="TRANSMITTAL_RESPONSE_OVERDUE",
                performed_by=None,
                reason="Response due date elapsed",
                metadata_json={
                    "recipient_ref": row.recipient_ref,
                    "due_at": row.due_at.isoformat() if row.due_at else None,
                },
            )
            db.execute(
                items.update()
                .where(
                    items.c.tenant_id == tenant_id,
                    items.c.transmittal_item_id == row.transmittal_item_id,
                )
                .values(
                    item_status="OVERDUE",
                    issue_status="RESPONSE_OVERDUE",
                    metadata_json={
                        **dict(item.metadata_json or {}),
                        "acknowledgement_id": row.acknowledgement_id,
                        "lifecycle_event_ids": event_ids,
                    },
                    modified_at=_now(),
                )
            )
            changed_items.append(row.transmittal_item_id)

    if rows:
        db.commit()

    return {
        "overdue_acknowledgement_count": len(rows),
        "transmittal_item_ids": changed_items,
        "transmittal_id": transmittal_id,
    }
