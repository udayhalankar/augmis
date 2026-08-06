from datetime import datetime, timedelta
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.db_models import (
    AuditLog,
    ConnectorFile,
    Document,
    Repository,
    SymployeeApprovalRecord,
    SymployeeAIRecommendation,
    SymployeeConnectorCommand,
    SymployeeDefinition,
    SymployeeDocumentIdentity,
    SymployeeDocumentSourceObject,
    SymployeeDocumentVersion,
    SymployeePolicyConfig,
    SymployeeWorkflowInstance,
    SymployeeWorkflowTask,
    Tenant,
    User,
)
from app.services import symployee_document_service as document_service
from app.services import symployee_workflow_service as workflow_service
from app.services.symployee_policy_service import resolve_required_policies


class SymployeeWorkflowServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            self.engine,
            tables=[
                Tenant.__table__,
                User.__table__,
                Repository.__table__,
                Document.__table__,
                ConnectorFile.__table__,
                AuditLog.__table__,
                SymployeeDefinition.__table__,
                SymployeePolicyConfig.__table__,
                SymployeeDocumentIdentity.__table__,
                SymployeeDocumentSourceObject.__table__,
                SymployeeDocumentVersion.__table__,
                SymployeeAIRecommendation.__table__,
                SymployeeApprovalRecord.__table__,
                SymployeeConnectorCommand.__table__,
                SymployeeWorkflowInstance.__table__,
                SymployeeWorkflowTask.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.original_now = workflow_service._now
        self.original_document_now = document_service._now
        workflow_service._now = lambda: datetime(2026, 1, 1, 12, 0, 0)
        document_service._now = lambda: datetime(2026, 1, 1, 12, 0, 0)
        self._seed_live_intake_chain()

    def tearDown(self):
        workflow_service._now = self.original_now
        document_service._now = self.original_document_now
        self.db.close()

    def _seed_live_intake_chain(self):
        self.db.add(Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"))
        self.db.add_all(
            [
                User(
                    user_id="USER-1",
                    tenant_id="TENANT-1",
                    name="Reviewer One",
                    email="reviewer.one@example.com",
                    password_hash="x",
                    role="tenant_admin",
                    status="ACTIVE",
                ),
                User(
                    user_id="USER-2",
                    tenant_id="TENANT-1",
                    name="Reviewer Two",
                    email="reviewer.two@example.com",
                    password_hash="x",
                    role="tenant_admin",
                    status="ACTIVE",
                ),
            ]
        )
        self.db.add(
            Repository(
                repository_id="REPO-1",
                tenant_id="TENANT-1",
                repository_name="Shared Drive",
                source_type="shared_drive",
                business_area="contracts",
            )
        )
        self.db.add(
            SymployeeDefinition(
                symployee_id="SYM-1",
                tenant_id="TENANT-1",
                code="document_controller",
                name="Document Controller",
            )
        )
        self.db.add_all(
            [
                SymployeePolicyConfig(
                    policy_id="POL-REVIEWER",
                    tenant_id="TENANT-1",
                    symployee_code="document_controller",
                    policy_domain="reviewer_assignment",
                    policy_code="default_document_reviewer_assignment",
                    name="Reviewer Assignment",
                    version_no=1,
                    status="ACTIVE",
                    is_default=True,
                    config_json={
                        "default_assignment": {
                            "role_code": "tenant_admin",
                            "strategy": "least_loaded_in_role",
                        },
                        "task_assignments": {
                            "classification_review": {
                                "role_code": "tenant_admin",
                                "strategy": "least_loaded_in_role",
                            },
                            "metadata_review": {
                                "role_code": "tenant_admin",
                                "strategy": "least_loaded_in_role",
                            },
                        },
                    },
                ),
                SymployeePolicyConfig(
                    policy_id="POL-SLA",
                    tenant_id="TENANT-1",
                    symployee_code="document_controller",
                    policy_domain="sla_rules",
                    policy_code="default_document_sla_rules",
                    name="SLA Rules",
                    version_no=1,
                    status="ACTIVE",
                    is_default=True,
                    config_json={
                        "default_rule": {
                            "target_hours": 2,
                            "warning_before_hours": 1,
                            "escalate_after_hours": 1,
                        }
                    },
                ),
            ]
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
                title="Contract Document",
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
                revision_code="1",
                version_label="REV-1",
                file_name="contract.pdf",
            )
        )
        self.db.add(
            SymployeeDocumentSourceObject(
                source_object_id="SRC-1",
                tenant_id="TENANT-1",
                identity_id="SID-1",
                repository_id="REPO-1",
                source_system_type="connector",
                external_object_id="EXT-1",
                source_path="D:\\Shared\\contract.pdf",
                source_version_ref="1",
                is_active=True,
            )
        )
        self.db.add_all(
            [
                SymployeeAIRecommendation(
                    recommendation_id="REC-CLASS",
                    tenant_id="TENANT-1",
                    symployee_id="SYM-1",
                    identity_id="SID-1",
                    version_id="SVR-1",
                    recommendation_type="classification",
                    status="NEEDS_REVIEW",
                    recommendation_json={"document_type_code": "contract"},
                    confidence_score=0.9,
                ),
                SymployeeAIRecommendation(
                    recommendation_id="REC-META",
                    tenant_id="TENANT-1",
                    symployee_id="SYM-1",
                    identity_id="SID-1",
                    version_id="SVR-1",
                    recommendation_type="metadata_extraction",
                    status="NEEDS_REVIEW",
                    recommendation_json={"fields": {"priority": "critical"}},
                    confidence_score=0.8,
                ),
            ]
        )
        self.db.add(
            SymployeeConnectorCommand(
                command_id="CMD-1",
                tenant_id="TENANT-1",
                repository_id="REPO-1",
                identity_id="SID-1",
                version_id="SVR-1",
                command_type="update_register",
                status="PENDING_APPROVAL",
                approval_status="PENDING_APPROVAL",
                payload_json={"target": "mdr"},
            )
        )
        self.db.add(
            SymployeeApprovalRecord(
                approval_id="APR-1",
                tenant_id="TENANT-1",
                approval_subject_type="recommendation",
                approval_subject_id="REC-CLASS",
                decision="APPROVED",
                approver_user_id="USER-1",
            )
        )
        self.db.commit()

    def test_live_intake_chain_creates_routed_workflow_tasks(self):
        result = workflow_service.sync_document_workflow(
            db=self.db,
            tenant_id="TENANT-1",
            symployee_id="SYM-1",
            identity_id="SID-1",
            version_id="SVR-1",
        )

        self.assertEqual(result["workflow_status"], "ACTIVE")
        self.assertEqual(result["routing_status"], "ROUTED")
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["pending_task_count"], 2)

        tasks = {task["task_code"]: task for task in result["tasks"]}
        self.assertIn("classification_review", tasks)
        self.assertIn("metadata_review", tasks)
        self.assertEqual(tasks["classification_review"]["assigned_role_code"], "tenant_admin")
        self.assertIsNotNone(tasks["classification_review"]["assigned_user_id"])
        self.assertEqual(tasks["classification_review"]["sla_status"], "ON_TRACK")
        self.assertEqual(tasks["classification_review"]["escalation_status"], "NONE")

    def test_policy_resolver_prefers_repository_scope_over_tenant_default(self):
        self.db.add(
            SymployeePolicyConfig(
                policy_id="POL-SLA-REPO",
                tenant_id="TENANT-1",
                symployee_code="document_controller",
                policy_domain="sla_rules",
                policy_code="repo_sla_rules",
                name="Repository SLA Rules",
                version_no=1,
                status="ACTIVE",
                is_default=True,
                scope_type="repository",
                scope_ref="REPO-1",
                config_json={
                    "default_rule": {
                        "target_hours": 4,
                        "warning_before_hours": 1,
                        "escalate_after_hours": 2,
                    }
                },
            )
        )
        self.db.commit()

        policies = resolve_required_policies(
            db=self.db,
            tenant_id="TENANT-1",
            policy_domains=["sla_rules"],
            repository_id="REPO-1",
            business_area="contracts",
            project_code="AKML",
        )

        self.assertEqual(policies["sla_rules"]["policy_code"], "repo_sla_rules")
        self.assertEqual(policies["sla_rules"]["scope_type"], "repository")
        self.assertEqual(policies["sla_rules"]["scope_ref"], "REPO-1")

    def test_sla_transitions_generate_reminder_and_escalation_notifications(self):
        workflow_service.sync_document_workflow(
            db=self.db,
            tenant_id="TENANT-1",
            symployee_id="SYM-1",
            identity_id="SID-1",
            version_id="SVR-1",
        )

        task = (
            self.db.query(SymployeeWorkflowTask)
            .filter(SymployeeWorkflowTask.task_code == "classification_review")
            .one()
        )
        task.due_at = workflow_service._now() + timedelta(minutes=30)
        self.db.commit()

        workflow_service.refresh_workflow_sla_states(self.db, "TENANT-1", "SID-1")
        self.db.refresh(task)
        self.assertEqual(task.sla_status, "WARNING")
        self.assertEqual(task.escalation_status, "WARNING")
        self.assertIn(
            "reminder_generated",
            [event["event_code"] for event in task.task_payload_json["workflow_events"]],
        )

        task.due_at = workflow_service._now() - timedelta(hours=2)
        self.db.commit()

        workflow_service.refresh_workflow_sla_states(self.db, "TENANT-1", "SID-1")
        self.db.refresh(task)
        self.assertEqual(task.sla_status, "OVERDUE")
        self.assertEqual(task.escalation_status, "ESCALATED")
        event_codes = [event["event_code"] for event in task.task_payload_json["workflow_events"]]
        self.assertIn("task_overdue", event_codes)
        self.assertIn("task_escalated", event_codes)

        notification_types = {
            row.event_type
            for row in self.db.query(AuditLog)
            .filter(AuditLog.event_category == "SYNTHETIC_EMPLOYEE_NOTIFICATION")
            .all()
        }
        self.assertIn("SYMPLOYEE_WORKFLOW_REMINDER", notification_types)
        self.assertIn("SYMPLOYEE_WORKFLOW_ESCALATED", notification_types)

    def test_document_controller_overview_exposes_analytics_breakdowns(self):
        workflow_service.sync_document_workflow(
            db=self.db,
            tenant_id="TENANT-1",
            symployee_id="SYM-1",
            identity_id="SID-1",
            version_id="SVR-1",
        )

        overview = document_service.get_document_controller_overview(self.db, "TENANT-1")

        self.assertEqual(overview["total_documents"], 1)
        self.assertEqual(overview["pending_recommendations"], 2)
        self.assertEqual(overview["pending_commands"], 1)
        self.assertEqual(overview["approved_items"], 1)
        self.assertEqual(overview["analytics"]["register"]["documents_requiring_attention"], 1)
        self.assertEqual(overview["analytics"]["review"]["pending_tasks"], 2)
        self.assertEqual(overview["analytics"]["commands"]["failed_commands"], 0)
        self.assertEqual(
            overview["analytics"]["breakdowns"]["by_repository"][0]["label"],
            "Shared Drive",
        )

    def test_master_document_register_includes_operational_fields(self):
        workflow_service.sync_document_workflow(
            db=self.db,
            tenant_id="TENANT-1",
            symployee_id="SYM-1",
            identity_id="SID-1",
            version_id="SVR-1",
        )

        register = document_service.build_master_document_register(self.db, "TENANT-1")
        row = register["items"][0]

        self.assertEqual(register["summary"]["total_documents"], 1)
        self.assertEqual(row["current_revision_code"], "1")
        self.assertEqual(row["source_path"], "D:\\Shared\\contract.pdf")
        self.assertEqual(row["pending_recommendation_count"], 2)
        self.assertEqual(row["pending_command_count"], 1)
        self.assertEqual(row["open_workflow_task_count"], 2)
        self.assertEqual(row["metadata_completeness_pct"], 100.0)
        self.assertIn("review_pending", row["attention_flags"])


if __name__ == "__main__":
    unittest.main()
