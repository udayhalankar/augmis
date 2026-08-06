from datetime import datetime
import unittest

from sqlalchemy import Column, DateTime, JSON, String, Table, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    Document,
    Repository,
    SymployeeDocumentIdentity,
    SymployeeDocumentVersion,
    SymployeeRecordAssignmentRule,
    SymployeeRecordDeclaration,
    SymployeeRecordDeclarationRule,
    SymployeeRecordLifecycleRule,
    SymployeeRecordVitalPolicy,
    SymployeeRetentionSchedule,
    Tenant,
    User,
)
from app.services import symployee_lifecycle_service as lifecycle_service
from app.services import symployee_records_service as records_service


_LIFECYCLE_EVENTS_TABLE = Base.metadata.tables.get("symployee_document_lifecycle_events")
if _LIFECYCLE_EVENTS_TABLE is None:
    _LIFECYCLE_EVENTS_TABLE = Table(
        "symployee_document_lifecycle_events",
        Base.metadata,
        Column("event_id", String, primary_key=True),
        Column("tenant_id", String, nullable=False),
        Column("identity_id", String, nullable=False),
        Column("version_id", String, nullable=True),
        Column("event_type", String, nullable=False),
        Column("state_dimension", String, nullable=False),
        Column("previous_state", String, nullable=True),
        Column("new_state", String, nullable=False),
        Column("event_date", DateTime(timezone=True), nullable=False),
        Column("performed_by", String, nullable=True),
        Column("reason", String, nullable=True),
        Column("workflow_instance_id", String, nullable=True),
        Column("transmittal_id", String, nullable=True),
        Column("approval_id", String, nullable=True),
        Column("metadata_json", JSON, nullable=True),
        Column("created_by", String, nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("modified_by", String, nullable=True),
        Column("modified_at", DateTime(timezone=True), nullable=False),
    )


class SymployeeRecordsServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                Tenant.__table__,
                User.__table__,
                Repository.__table__,
                Document.__table__,
                SymployeeDocumentIdentity.__table__,
                SymployeeDocumentVersion.__table__,
                SymployeeRecordDeclaration.__table__,
                SymployeeRecordDeclarationRule.__table__,
                SymployeeRecordLifecycleRule.__table__,
                SymployeeRetentionSchedule.__table__,
                SymployeeRecordVitalPolicy.__table__,
                SymployeeRecordAssignmentRule.__table__,
                _LIFECYCLE_EVENTS_TABLE,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 7, 21, 10, 0, 0)
        self.original_records_now = records_service._now
        self.original_lifecycle_now = lifecycle_service._now
        self.original_resolve_retention_rule = records_service.resolve_retention_rule
        records_service._now = lambda: self.fixed_now
        lifecycle_service._now = lambda: self.fixed_now
        records_service.resolve_retention_rule = lambda *args, **kwargs: None
        self._seed_core_entities()

    def tearDown(self):
        records_service._now = self.original_records_now
        lifecycle_service._now = self.original_lifecycle_now
        records_service.resolve_retention_rule = self.original_resolve_retention_rule
        self.db.close()

    def _seed_core_entities(self):
        self.db.add(Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"))
        self.db.add(
            User(
                user_id="USER-1",
                tenant_id="TENANT-1",
                name="Records Admin",
                email="records.admin@example.com",
                password_hash="x",
                role="tenant_admin",
                status="ACTIVE",
            )
        )
        self.db.add(
            Repository(
                repository_id="REPO-1",
                tenant_id="TENANT-1",
                repository_name="Repository One",
                source_type="shared_drive",
                business_area="contracts",
            )
        )
        self.db.add(
            Document(
                document_id="DOC-1",
                tenant_id="TENANT-1",
                repository_id="REPO-1",
                file_name="contract.pdf",
                original_file_name="contract.pdf",
                source_type="shared_drive",
                business_area="contracts",
            )
        )
        self.db.add(
            SymployeeDocumentIdentity(
                identity_id="SID-1",
                tenant_id="TENANT-1",
                repository_id="REPO-1",
                canonical_document_number="DOC-001",
                title="Contract Record",
                document_type_code="contract",
                discipline_code="legal",
                project_code="AKML",
                originator_code="ORG",
                current_document_id="DOC-1",
                current_version_id="SVR-1",
            )
        )
        self.db.add(
            SymployeeDocumentVersion(
                version_id="SVR-1",
                tenant_id="TENANT-1",
                identity_id="SID-1",
                document_id="DOC-1",
                revision_code="A",
                version_label="REV-A",
                file_name="contract.pdf",
                file_extension="pdf",
                status="ACTIVE",
            )
        )
        self.db.commit()

    def _seed_record_rules(self):
        self.db.add(
            SymployeeRecordDeclarationRule(
                declaration_rule_id="SRDR-1",
                tenant_id="TENANT-1",
                rule_code="DECL-1",
                rule_name="Contract declaration",
                record_category_code="PROJECT_RECORD",
                declaration_mode="DIRECT_DECLARE",
                approval_required=False,
                candidate_trigger_event="INGESTION",
                declaration_trigger_event="MANUAL",
                matching_criteria_json={},
                status="ACTIVE",
                effective_from=self.fixed_now,
                version_no=1,
                is_current_version=True,
                rule_priority=100,
            )
        )
        self.db.add(
            SymployeeRecordLifecycleRule(
                lifecycle_rule_id="SRLR-1",
                tenant_id="TENANT-1",
                rule_code="LIFE-1",
                rule_name="Immediate active",
                record_category_code="PROJECT_RECORD",
                active_start_event="DECLARED_RECORD",
                inactive_eligibility_event="WORKFLOW_COMPLETED",
                inactive_after_days=0,
                status="ACTIVE",
                effective_from=self.fixed_now,
                version_no=1,
                is_current_version=True,
                rule_priority=100,
            )
        )
        self.db.commit()

    def test_declare_record_uses_first_lifecycle_event_as_source_event(self):
        self._seed_record_rules()

        result = records_service.declare_record(
            self.db,
            "TENANT-1",
            identity_id="SID-1",
            version_id="SVR-1",
            record_category="PROJECT_RECORD",
            declared_by="USER-1",
            declaration_reason="Regression validation",
        )

        declaration = (
            self.db.query(SymployeeRecordDeclaration)
            .filter(SymployeeRecordDeclaration.record_declaration_id == result["record_declaration_id"])
            .one()
        )
        transition_events = list(result["lifecycle_transition"]["events"])
        declared_event = next(
            event for event in transition_events if event["event_type"] == "RECORD_DECLARED"
        )
        active_event = next(
            event for event in transition_events if event["event_type"] == "RECORD_BECAME_ACTIVE"
        )

        self.assertEqual(result["source_event_id"], declared_event["event_id"])
        self.assertEqual(declaration.source_event_id, declared_event["event_id"])
        self.assertNotEqual(declaration.source_event_id, active_event["event_id"])

    def test_declare_record_activates_when_lifecycle_rule_matches_declared_record_trigger(self):
        self._seed_record_rules()

        result = records_service.declare_record(
            self.db,
            "TENANT-1",
            identity_id="SID-1",
            version_id="SVR-1",
            record_category="PROJECT_RECORD",
            declared_by="USER-1",
            declaration_reason="Regression validation",
        )

        declaration = (
            self.db.query(SymployeeRecordDeclaration)
            .filter(SymployeeRecordDeclaration.record_declaration_id == result["record_declaration_id"])
            .one()
        )
        active_events = [
            event
            for event in result["lifecycle_transition"]["events"]
            if event["event_type"] == "RECORD_BECAME_ACTIVE"
        ]

        self.assertEqual(result["record_status"], "DECLARED_RECORD")
        self.assertEqual(result["activity_stage"], "ACTIVE")
        self.assertEqual(declaration.record_stage, "ACTIVE")
        self.assertIsNotNone(declaration.active_from)
        self.assertEqual(len(active_events), 1)

    def test_resolve_config_row_prefers_specific_scope_then_lower_rule_priority(self):
        self.db.add_all(
            [
                SymployeeRecordAssignmentRule(
                    assignment_rule_id="SRAR-1",
                    tenant_id="TENANT-1",
                    rule_code="ASSIGN-TENANT",
                    rule_name="Tenant level",
                    assignment_context="DECLARATION",
                    owner_role_code="records_officer",
                    status="ACTIVE",
                    effective_from=self.fixed_now,
                    version_no=1,
                    is_current_version=True,
                    rule_priority=1,
                ),
                SymployeeRecordAssignmentRule(
                    assignment_rule_id="SRAR-2",
                    tenant_id="TENANT-1",
                    rule_code="ASSIGN-PROJECT",
                    rule_name="Project level",
                    project_code="AKML",
                    assignment_context="DECLARATION",
                    owner_role_code="project_records_owner",
                    status="ACTIVE",
                    effective_from=self.fixed_now,
                    version_no=1,
                    is_current_version=True,
                    rule_priority=999,
                ),
                SymployeeRecordAssignmentRule(
                    assignment_rule_id="SRAR-3",
                    tenant_id="TENANT-1",
                    rule_code="ASSIGN-PROJECT-HIGHER",
                    rule_name="Project level preferred",
                    project_code="AKML",
                    assignment_context="DECLARATION",
                    owner_role_code="project_records_owner_preferred",
                    status="ACTIVE",
                    effective_from=self.fixed_now,
                    version_no=1,
                    is_current_version=True,
                    rule_priority=10,
                ),
            ]
        )
        self.db.commit()

        identity = (
            self.db.query(SymployeeDocumentIdentity)
            .filter(SymployeeDocumentIdentity.identity_id == "SID-1")
            .one()
        )
        selected = records_service._resolve_config_row(
            self.db,
            "TENANT-1",
            identity=identity,
            table_name="symployee_record_assignment_rules",
            extra_filters={"assignment_context": ["DECLARATION"]},
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["assignment_rule_id"], "SRAR-3")
        self.assertEqual(selected["owner_role_code"], "project_records_owner_preferred")


if __name__ == "__main__":
    unittest.main()
