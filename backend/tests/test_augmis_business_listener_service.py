from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import augmis_business as augmis_business_routes
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentDiscoveryTranslation,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProvider,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.models.augmis_business_models import (
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessConnectorUpdateRequest,
    AugmisBusinessSearchProfileCreateRequest,
)
from app.services import augmis_business_listener_service as service


class AugmisBusinessListenerServiceTest(unittest.TestCase):
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
                AuditLog.__table__,
                BusinessDevelopmentExperienceItem.__table__,
                BusinessDevelopmentOpportunity.__table__,
                BusinessDevelopmentSearchProfile.__table__,
                BusinessDevelopmentSearchProvider.__table__,
                BusinessDevelopmentConnector.__table__,
                BusinessDevelopmentConnectorRun.__table__,
                BusinessDevelopmentDiscoveredOpportunity.__table__,
                BusinessDevelopmentDiscoveryTranslation.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 7, 11, 0, 0, tzinfo=timezone.utc)
        self.original_now = service._now
        service._now = lambda: self.fixed_now
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": [
                "business_development:read",
                "business_development:create",
                "business_development:update",
                "business_development:scan",
                "business_development:admin",
            ],
            "allowed_modules": ["augmis_business"],
        }
        self.read_only_user = {
            **self.current_user,
            "permissions": ["business_development:read"],
        }
        self._seed_core()

    def tearDown(self):
        service._now = self.original_now
        self.db.close()

    def _seed_core(self):
        self.db.add_all(
            [
                Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"),
                Tenant(tenant_id="TENANT-2", tenant_name="Tenant 2"),
                User(
                    user_id="USER-1",
                    tenant_id="TENANT-1",
                    name="Business Admin",
                    email="bd.admin@example.com",
                    password_hash="x",
                    role="tenant_admin",
                    status="ACTIVE",
                ),
                BusinessDevelopmentExperienceItem(
                    id="EXP-1",
                    tenant_id="TENANT-1",
                    name="Workflow Dashboard",
                    category="Applications",
                    description="Workflow and dashboard delivery experience.",
                    business_problems_json=["Manual workflows"],
                    features_json=["Approvals", "Dashboards"],
                    technologies_json=["React", "FastAPI"],
                    industries_json=["Utilities"],
                    keywords_json=["workflow", "dashboard", "portal"],
                    reusable_capabilities_json=["records management", "approval workflows"],
                    confidentiality_safe_summary="Reusable workflow experience.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def _make_ted_candidate(
        self,
        *,
        title: str,
        summary: str,
        cpv_codes: list[str],
        organization_name: str = "City Authority",
        closing_date: datetime | None = None,
    ):
        return service.AugmisBusinessDiscoveredOpportunityCandidate(
            external_id=f"TED-{abs(hash(title))}",
            source_type="public_procurement",
            source_name="TED",
            source_url="https://ted.europa.eu/en/notice/123456-2026/html",
            source_country="DEU",
            title=title,
            organization_name=organization_name,
            published_date=self.fixed_now,
            closing_date=closing_date,
            country="DEU",
            region=None,
            industry="Public Procurement",
            requirement_summary=summary,
            raw_summary=summary,
            raw_text=summary,
            budget_min=None,
            budget_max=None,
            currency=None,
            evidence=[],
            source_metadata={"provider": "ted", "cpv_codes": cpv_codes},
            raw_content_json={
                "provider": "ted",
                "cpv_codes": cpv_codes,
                "contract_nature": ["services"],
                "notice_type": "cn-standard",
            },
            retrieval_timestamp=self.fixed_now,
        )

    def test_default_profile_and_fixture_connector_are_seeded(self):
        profile = service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user)
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        self.assertEqual(profile.name, service.DEFAULT_PROFILE_NAME)
        self.assertEqual(connector.connector_type, service.FIXTURE_CONNECTOR_TYPE)

    def test_search_profile_create_and_update(self):
        created = service.create_search_profile(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessSearchProfileCreateRequest(
                name="Africa Focus",
                target_regions_json=["Africa"],
                include_keywords_json=["inspection"],
            ),
        )["data"]
        self.assertEqual(created["name"], "Africa Focus")
        updated = service.update_search_profile(
            self.db,
            "TENANT-1",
            created["id"],
            self.current_user,
            service.AugmisBusinessSearchProfileUpdateRequest(enabled=False),  # type: ignore[attr-defined]
        )["data"]
        self.assertFalse(updated["enabled"])

    def test_fixture_scan_creates_new_duplicate_and_filtered_counts(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        profile = service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user)
        profile.include_keywords_json = []
        profile.include_technologies_json = []
        profile.include_capabilities_json = []
        profile.exclude_keywords_json = ["records management"]
        self.db.commit()
        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]
        run = result["run"]
        self.assertEqual(run["items_found"], 3)
        self.assertEqual(run["items_duplicate"], 1)
        self.assertEqual(run["items_filtered"], 1)
        self.assertEqual(run["items_new"], 1)

    def test_repeat_scan_counts_existing_external_ids_as_duplicates_without_error(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        first = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]
        second = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]

        self.assertEqual(first["status"], "completed")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["items_new"], 0)
        self.assertEqual(second["items_duplicate"], 3)
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(connector_row.status, "ready")
        self.assertIsNone(connector_row.last_error_message)

    def test_overlap_protection_blocks_second_running_scan(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        running = BusinessDevelopmentConnectorRun(
            id="BD-RUN-LOCK-1",
            tenant_id="TENANT-1",
            connector_id=connector.id,
            run_type="manual",
            status="running",
            started_at=self.fixed_now,
            run_metadata_json={},
            initiated_by="USER-1",
        )
        self.db.add(running)
        self.db.commit()
        with self.assertRaises(Exception) as exc:
            service.run_connector_scan(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                AugmisBusinessConnectorScanRequest(run_type="manual"),
            )
        self.assertIn("already in progress", str(exc.exception))

    def test_import_discovery_creates_opportunity_and_blocks_repeat(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )
        discovery = (
            self.db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(
                BusinessDevelopmentDiscoveredOpportunity.tenant_id == "TENANT-1",
                BusinessDevelopmentDiscoveredOpportunity.discovery_status == "new",
            )
            .first()
        )
        self.assertIsNotNone(discovery)
        result = service.import_discovery_as_opportunity(
            self.db,
            "TENANT-1",
            discovery.id,  # type: ignore[union-attr]
            self.current_user,
        )["data"]
        self.assertEqual(result["discovery"]["discovery_status"], "imported")
        self.assertTrue(result["opportunity"]["id"].startswith("BD-OPP-"))
        with self.assertRaises(Exception) as exc:
            service.import_discovery_as_opportunity(
                self.db,
                "TENANT-1",
                discovery.id,  # type: ignore[union-attr]
                self.current_user,
            )
        self.assertIn("already been imported", str(exc.exception))

    def test_list_discoveries_is_tenant_scoped(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )
        rows = service.list_discoveries(self.db, "TENANT-2")["data"]
        self.assertEqual(rows, [])

    def test_same_source_type_can_serialize_different_provider_identity(self):
        independent_connector = service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        ted_connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        self.db.add_all(
            [
                BusinessDevelopmentDiscoveredOpportunity(
                    id="DISC-AUGMIS",
                    tenant_id="TENANT-1",
                    connector_id=independent_connector.id,
                    connector_run_id=None,
                    external_id="AUGMIS-1",
                    source_type="public_procurement",
                    source_name="AUGMIS Web",
                    source_url="https://buyer.example/tenders/1",
                    canonical_source_url="https://buyer.example/tenders/1",
                    source_domain="buyer.example",
                    source_country="IND",
                    title="Workflow Automation RFP",
                    normalized_title="workflow automation rfp",
                    organization_name="Buyer",
                    normalized_organization_name="buyer",
                    raw_summary="Workflow automation",
                    requirement_summary="Workflow automation",
                    normalized_content_json={},
                    raw_content_json={"provider": "augmis_internal", "page_type": "rfp"},
                    raw_text="Workflow automation",
                    country="IND",
                    region=None,
                    industry=None,
                    budget_min=None,
                    budget_max=None,
                    currency=None,
                    discovered_at=self.fixed_now,
                    retrieval_timestamp=self.fixed_now,
                    discovery_status="new",
                    duplicate_of_discovery_id=None,
                    possible_duplicate_of_discovery_id=None,
                    imported_opportunity_id=None,
                    preliminary_relevance_score=55.0,
                    relevance_reasons_json=[],
                    matched_keywords_json=[],
                    evidence_json=[],
                    normalized_search_text="workflow automation",
                    url_fingerprint="augmis1",
                    composite_fingerprint="augmis1",
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentDiscoveredOpportunity(
                    id="DISC-TED",
                    tenant_id="TENANT-1",
                    connector_id=ted_connector.id,
                    connector_run_id=None,
                    external_id="TED-1",
                    source_type="public_procurement",
                    source_name="TED",
                    source_url="https://ted.example/1",
                    canonical_source_url="https://ted.example/1",
                    source_domain="ted.example",
                    source_country="DEU",
                    title="Digital Health Support",
                    normalized_title="digital health support",
                    organization_name="Authority",
                    normalized_organization_name="authority",
                    raw_summary="Digital health support",
                    requirement_summary="Digital health support",
                    normalized_content_json={},
                    raw_content_json={"provider": "ted"},
                    raw_text="Digital health support",
                    country="DEU",
                    region=None,
                    industry=None,
                    budget_min=None,
                    budget_max=None,
                    currency=None,
                    discovered_at=self.fixed_now,
                    retrieval_timestamp=self.fixed_now,
                    discovery_status="new",
                    duplicate_of_discovery_id=None,
                    possible_duplicate_of_discovery_id=None,
                    imported_opportunity_id=None,
                    preliminary_relevance_score=55.0,
                    relevance_reasons_json=[],
                    matched_keywords_json=[],
                    evidence_json=[],
                    normalized_search_text="digital health support",
                    url_fingerprint="ted1",
                    composite_fingerprint="ted1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

        rows = service.list_discoveries(self.db, "TENANT-1")["data"]
        row_by_id = {row["id"]: row for row in rows}
        self.assertEqual(row_by_id["DISC-AUGMIS"]["display_source"], "AUGMIS Web")
        self.assertEqual(row_by_id["DISC-AUGMIS"]["source_provider_key"], "augmis_internal")
        self.assertEqual(row_by_id["DISC-TED"]["display_source"], "TED")
        self.assertEqual(row_by_id["DISC-TED"]["source_provider_key"], "ted")

    def test_original_raw_payload_preserved(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        connector_run = BusinessDevelopmentConnectorRun(
            id="BD-RUN-RAW-1",
            tenant_id="TENANT-1",
            connector_id=connector.id,
            run_type="manual",
            status="running",
            started_at=self.fixed_now,
            run_metadata_json={},
            initiated_by="USER-1",
        )
        self.db.add(connector_run)
        self.db.commit()
        candidate = service.AugmisBusinessDiscoveredOpportunityCandidate(
            external_id="RAW-HTML-1",
            source_type="employment_contract",
            source_name="Remote OK",
            source_url="https://example.com/jobs/1",
            source_country="GBR",
            title="Workflow Automation Engineer",
            organization_name="Acme",
            published_date=self.fixed_now,
            closing_date=None,
            country="GBR",
            region="London",
            industry="Software",
            requirement_summary='<p onclick="alert(1)">Build <strong>workflow</strong> dashboards</p>',
            raw_summary='<p onclick="alert(1)">Build <strong>workflow</strong> dashboards</p>',
            raw_text='<p onclick="alert(1)">Build <strong>workflow</strong> dashboards</p>',
            budget_min=5000,
            budget_max=8000,
            currency="GBP",
            evidence=[],
            source_metadata={"provider": "remoteok"},
            raw_content_json={
                "provider_description": '<p onclick="alert(1)">Build <strong>workflow</strong> dashboards</p>',
                "provider_payload": {"html": True},
            },
            retrieval_timestamp=self.fixed_now,
        )

        result = service.ingest_discovered_opportunity(
            self.db,
            "TENANT-1",
            connector,
            connector_run,
            candidate,
            service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user),
        )

        row = service._require_discovery(self.db, "TENANT-1", result.row.id)
        self.assertEqual(row.raw_content_json["provider_description"], candidate.raw_content_json["provider_description"])
        self.assertEqual(row.requirement_summary, "Build workflow dashboards")
        self.assertIn("<strong>workflow</strong>", row.normalized_content_json["requirement"]["safe_html"])

    def test_content_backfill_tenant_scoped(self):
        self.db.add_all(
            [
                BusinessDevelopmentDiscoveredOpportunity(
                    id="BD-DISC-1",
                    tenant_id="TENANT-1",
                    connector_id="BD-CNX-1",
                    connector_run_id=None,
                    external_id="DISC-1",
                    source_type="web_search",
                    source_name="Web Search",
                    title="Tenant One",
                    normalized_title="tenant one",
                    organization_name="Org One",
                    normalized_organization_name="org one",
                    requirement_summary="<p>Tenant <strong>One</strong></p>",
                    raw_summary="<p>Tenant <strong>One</strong></p>",
                    raw_text="<p>Tenant <strong>One</strong></p>",
                    raw_content_json={"original": "<p>Tenant <strong>One</strong></p>"},
                    normalized_content_json={},
                    discovery_status="new",
                    evidence_json=[],
                    matched_keywords_json=[],
                    relevance_reasons_json=[],
                    discovered_at=self.fixed_now,
                    retrieval_timestamp=self.fixed_now,
                    created_at=self.fixed_now,
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentDiscoveredOpportunity(
                    id="BD-DISC-2",
                    tenant_id="TENANT-2",
                    connector_id="BD-CNX-2",
                    connector_run_id=None,
                    external_id="DISC-2",
                    source_type="web_search",
                    source_name="Web Search",
                    title="Tenant Two",
                    normalized_title="tenant two",
                    organization_name="Org Two",
                    normalized_organization_name="org two",
                    requirement_summary="<p>Tenant <strong>Two</strong></p>",
                    raw_summary="<p>Tenant <strong>Two</strong></p>",
                    raw_text="<p>Tenant <strong>Two</strong></p>",
                    raw_content_json={"original": "<p>Tenant <strong>Two</strong></p>"},
                    normalized_content_json={},
                    discovery_status="new",
                    evidence_json=[],
                    matched_keywords_json=[],
                    relevance_reasons_json=[],
                    discovered_at=self.fixed_now,
                    retrieval_timestamp=self.fixed_now,
                    created_at=self.fixed_now,
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

        result = service.reprocess_discovery_content(
            self.db,
            "TENANT-1",
            self.current_user,
            limit=10,
        )

        self.assertEqual(result["data"]["count"], 1)
        tenant_one = service._require_discovery(self.db, "TENANT-1", "BD-DISC-1")
        tenant_two = service._require_discovery(self.db, "TENANT-2", "BD-DISC-2")
        self.assertEqual(tenant_one.requirement_summary, "Tenant One")
        self.assertEqual(tenant_one.raw_content_json["original"], "<p>Tenant <strong>One</strong></p>")
        self.assertTrue(tenant_one.normalized_content_json["requirement"]["safe_html"].startswith("<p>"))
        self.assertEqual(tenant_two.requirement_summary, "<p>Tenant <strong>Two</strong></p>")
        self.assertEqual(tenant_two.normalized_content_json, {})

    def test_update_connector_enables_and_disables_status(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        disabled = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorUpdateRequest(enabled=False),
        )["data"]
        self.assertEqual(disabled["status"], "disabled")

    def test_connector_schedule_can_be_enabled(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        updated = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=360,
                schedule_timezone="UTC",
            ),
        )["data"]
        self.assertTrue(updated["schedule_enabled"])
        self.assertEqual(updated["schedule_type"], "hourly_interval")
        self.assertEqual(updated["schedule_expression"], "Every 6 hours")
        self.assertEqual(updated["next_run_at"], "2026-08-07T17:00:00")

    def test_connector_schedule_can_be_disabled(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=360,
                schedule_timezone="UTC",
            ),
        )
        updated = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(enabled=True, schedule_enabled=False),  # type: ignore[attr-defined]
        )["data"]
        self.assertFalse(updated["schedule_enabled"])
        self.assertEqual(updated["schedule_type"], "manual")
        self.assertIsNone(updated["next_run_at"])

    def test_daily_schedule_computes_next_run(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        updated = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="daily",
                schedule_time_local="07:00",
                schedule_timezone="UTC",
            ),
        )["data"]
        self.assertEqual(updated["next_run_at"], "2026-08-08T07:00:00")

    def test_weekly_schedule_computes_next_run(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        updated = service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="weekly",
                schedule_day_of_week=0,
                schedule_time_local="07:00",
                schedule_timezone="UTC",
            ),
        )["data"]
        self.assertEqual(updated["next_run_at"], "2026-08-10T07:00:00")

    def test_invalid_schedule_is_rejected(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        with self.assertRaises(Exception) as exc:
            service.update_connector(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                    schedule_enabled=True,
                    schedule_type="hourly_interval",
                    schedule_interval_minutes=30,
                    schedule_timezone="UTC",
                ),
            )
        self.assertIn("greater than or equal to 60", str(exc.exception))

    def test_due_connector_runs(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=60,
                schedule_timezone="UTC",
            ),
        )
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        connector_row.next_run_at = self.fixed_now - service.timedelta(minutes=1)  # type: ignore[attr-defined]
        self.db.commit()

        result = service.run_due_listener_scans(self.db)

        self.assertEqual(result["due_count"], 1)
        self.assertEqual(result["results"][0]["run_type"], "scheduled")
        latest_run = (
            self.db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.connector_id == connector.id)
            .order_by(BusinessDevelopmentConnectorRun.started_at.desc())
            .first()
        )
        self.assertIsNotNone(latest_run)
        self.assertEqual(latest_run.run_type, "scheduled")  # type: ignore[union-attr]

    def test_startup_does_not_scan_every_connector(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="daily",
                schedule_time_local="07:00",
                schedule_timezone="UTC",
            ),
        )
        run_count_before = self.db.query(BusinessDevelopmentConnectorRun).count()
        init_result = service.initialize_listener_schedule_state(self.db)
        run_count_after = self.db.query(BusinessDevelopmentConnectorRun).count()
        self.assertEqual(init_result["recovered"], 0)
        self.assertEqual(run_count_before, run_count_after)

    def test_stale_running_scan_is_recovered(self):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=360,
                schedule_timezone="UTC",
            ),
        )
        stale_started_at = self.fixed_now - service.timedelta(minutes=service.SCHEDULE_STALE_RUN_THRESHOLD_MINUTES + 5)
        run = BusinessDevelopmentConnectorRun(
            id="BD-RUN-STALE-1",
            tenant_id="TENANT-1",
            connector_id=connector.id,
            run_type="scheduled",
            status="running",
            started_at=stale_started_at,
            run_metadata_json={},
        )
        self.db.add(run)
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        connector_row.active_run_id = run.id
        self.db.commit()

        result = service.recover_stale_connector_runs(self.db)

        self.assertEqual(result["recovered"], 1)
        recovered_run = (
            self.db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.id == run.id)
            .first()
        )
        self.assertEqual(recovered_run.status, "failed")  # type: ignore[union-attr]
        refreshed_connector = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertIsNone(refreshed_connector.active_run_id)
        self.assertEqual(refreshed_connector.status, "attention")

    @patch("app.services.augmis_business_listener_service._get_connector_implementation")
    def test_transient_failure_schedules_retry(self, mock_get_implementation):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=360,
                schedule_timezone="UTC",
            ),
        )
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        connector_row.next_run_at = self.fixed_now - service.timedelta(minutes=1)  # type: ignore[attr-defined]
        self.db.commit()

        implementation = Mock()
        implementation.validate_config.return_value = None
        implementation.discover.side_effect = Exception("HTTP 503 temporary upstream timeout")
        implementation.last_run_metadata = {}
        mock_get_implementation.return_value = implementation

        result = service.run_due_listener_scans(self.db)

        self.assertEqual(result["due_count"], 1)
        refreshed_connector = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(refreshed_connector.schedule_retry_count, 1)
        self.assertIsNotNone(refreshed_connector.next_run_at)
        latest_run = (
            self.db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.connector_id == connector.id)
            .order_by(BusinessDevelopmentConnectorRun.started_at.desc())
            .first()
        )
        self.assertEqual(latest_run.next_retry_at.isoformat(), "2026-08-07T11:05:00")  # type: ignore[union-attr]

    @patch("app.services.augmis_business_listener_service._get_connector_implementation")
    def test_missing_credential_does_not_retry(self, mock_get_implementation):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.update_connector(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            service.AugmisBusinessConnectorUpdateRequest(  # type: ignore[attr-defined]
                schedule_enabled=True,
                schedule_type="hourly_interval",
                schedule_interval_minutes=360,
                schedule_timezone="UTC",
            ),
        )
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        connector_row.next_run_at = self.fixed_now - service.timedelta(minutes=1)  # type: ignore[attr-defined]
        self.db.commit()

        implementation = Mock()
        implementation.validate_config.return_value = None
        implementation.discover.side_effect = Exception("Provider credential is not configured.")
        implementation.last_run_metadata = {}
        mock_get_implementation.return_value = implementation

        service.run_due_listener_scans(self.db)

        refreshed_connector = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(refreshed_connector.schedule_retry_count, 0)

    def test_route_permission_enforcement_blocks_scan_without_permission(self):
        connector = service.ensure_fixture_connector(self.db, "TENANT-1", self.current_user)
        app = FastAPI()
        app.include_router(augmis_business_routes.router)

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: self.read_only_user
        client = TestClient(app)
        response = client.post(
            f"/api/augmis-business/connectors/{connector.id}/scan",
            json={"run_type": "manual"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.services.augmis_business_listener_service.test_connector_credential")
    def test_web_connector_test_uses_credential_resolution_path(self, mock_test_connector_credential: Mock):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        mock_test_connector_credential.return_value = {
            "data": {"result": {"success": True, "message": "Connection successful."}}
        }

        result = service.test_connector(self.db, "TENANT-1", self.current_user, connector.id)

        self.assertTrue(result["data"]["result"]["success"])
        mock_test_connector_credential.assert_called_once_with(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
        )

    @patch.object(service.WebOpportunitySearchConnector, "discover")
    @patch("app.services.augmis_business_listener_service.resolve_provider_credential")
    def test_web_connector_scan_uses_resolved_provider_credential(
        self,
        mock_resolve_provider_credential: Mock,
        mock_discover: Mock,
    ):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        resolved_credential = service.ResolvedProviderCredential(
            provider="tavily",
            api_key="tvly-tenant-1234",
            credential_source="tenant_secret",
        )
        mock_resolve_provider_credential.return_value = resolved_credential
        mock_discover.return_value = []

        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )

        self.assertTrue(result["success"])
        mock_resolve_provider_credential.assert_called_once_with(self.db, "TENANT-1", "tavily")
        self.assertIs(mock_discover.call_args.kwargs["credential"], resolved_credential)

    def test_web_connector_defaults_are_preserved_when_runtime_config_is_absent(self):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {"provider": "tavily"}
        self.db.commit()

        implementation = service.WebOpportunitySearchConnector()
        implementation.validate_config(connector.configuration_json)
        policy = service._effective_web_search_runtime_policy(connector.configuration_json)

        self.assertEqual(policy.max_fetch_bytes, 300000)
        self.assertEqual(policy.fetch_timeout_seconds, 15)
        self.assertEqual(policy.max_extracted_text_chars, 30000)
        self.assertEqual(policy.max_redirects, 3)

    def test_web_connector_runtime_limits_below_minimum_are_rejected(self):
        implementation = service.WebOpportunitySearchConnector()
        with self.assertRaisesRegex(Exception, "max_fetch_bytes must be between 25000 and 1000000"):
            implementation.validate_config(
                {
                    "provider": "tavily",
                    "max_fetch_bytes": 1000,
                }
            )

    def test_web_connector_runtime_limits_above_ceiling_are_rejected(self):
        implementation = service.WebOpportunitySearchConnector()
        with self.assertRaisesRegex(Exception, "fetch_timeout_seconds must be between 3 and 30"):
            implementation.validate_config(
                {
                    "provider": "tavily",
                    "fetch_timeout_seconds": 60,
                }
            )

    @patch("app.services.augmis_business_listener_service.fetch_public_webpage")
    @patch("app.services.augmis_business_listener_service.extract_text_from_webpage")
    @patch("app.services.augmis_business_listener_service.get_web_search_provider")
    @patch("app.services.augmis_business_listener_service.resolve_provider_credential")
    def test_web_connector_respects_max_source_fetches_per_scan(
        self,
        mock_resolve_provider_credential: Mock,
        mock_get_provider: Mock,
        mock_extract_text: Mock,
        mock_fetch_public_webpage: Mock,
    ):
        connector = service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        connector.configuration_json = {
            **(connector.configuration_json or {}),
            "max_source_fetches_per_scan": 1,
            "max_candidate_results": 10,
        }
        self.db.commit()
        mock_resolve_provider_credential.return_value = service.ResolvedProviderCredential(
            provider="tavily",
            api_key="tvly-tenant-1234",
            credential_source="tenant_secret",
        )
        mock_provider = Mock()
        mock_provider.name = "tavily"
        mock_provider.search.return_value = {
            "provider": "tavily",
            "query": "workflow",
            "count": 2,
            "raw_count": 2,
            "api_call_count": 1,
            "usage": {"credits": 1},
            "results": [
                type(
                    "Result",
                    (),
                    {
                        "result_id": "1",
                        "title": "Workflow Automation RFP",
                        "url": "https://buyer.example/rfp/workflow",
                        "snippet": "Seeking workflow automation vendor.",
                        "source_domain": "buyer.example",
                        "published_at": None,
                        "rank": 1,
                        "provider_metadata": {},
                    },
                )(),
                type(
                    "Result",
                    (),
                    {
                        "result_id": "2",
                        "title": "Reporting Dashboard Tender",
                        "url": "https://buyer.example/rfp/dashboard",
                        "snippet": "Seeking dashboard implementation vendor.",
                        "source_domain": "buyer.example",
                        "published_at": None,
                        "rank": 2,
                        "provider_metadata": {},
                    },
                )(),
            ],
        }
        mock_get_provider.return_value = mock_provider
        mock_fetch_public_webpage.return_value = {
            "url": "https://buyer.example/rfp/workflow",
            "status_code": 200,
            "content_type": "text/html",
            "body": "<html><body>Workflow automation proposal</body></html>",
            "bytes_read": 120,
        }
        mock_extract_text.return_value = "Workflow automation proposal"

        result = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
        )["data"]

        self.assertEqual(result["run"]["run_metadata_json"]["source_pages_attempted"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["source_pages_skipped_due_limit"], 1)
        self.assertEqual(mock_fetch_public_webpage.call_count, 1)

    def test_relevant_software_tender_gets_high_score(self):
        score, reasons, matched = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Workflow automation software platform for municipal services",
                summary="Custom software development, system integration, dashboards and office automation for a city service portal.",
                cpv_codes=["72230000", "72262000", "72513000"],
                organization_name="City of Hamburg",
            ),
            None,
        )
        self.assertGreaterEqual(score, 80.0)
        self.assertTrue(any("High-relevance software / IT CPV" in reason for reason in reasons))
        self.assertTrue(matched)

    def test_document_management_tender_gets_high_score(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Document management system renewal for city archives",
                summary="Upgrade, migration and implementation of a records management and archival information system.",
                cpv_codes=["48311100", "72512000", "72212311"],
                organization_name="Budapest City Archives",
            ),
            None,
        )
        self.assertGreaterEqual(score, 80.0)

    def test_data_analytics_tender_gets_high_score(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Analytics and dashboard platform for public reporting",
                summary="Business intelligence, statistical reporting and database services for a public authority.",
                cpv_codes=["72212482", "72316000", "72320000"],
                organization_name="Regional Data Agency",
            ),
            None,
        )
        self.assertGreaterEqual(score, 80.0)

    def test_pure_legal_services_tender_scores_low(self):
        score, reasons, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Legal advisory services for public energy project",
                summary="Comprehensive legal and financial advisory support for an energy efficiency programme.",
                cpv_codes=["79111000", "79410000"],
                organization_name="Ministry of Regional Development",
            ),
            None,
        )
        self.assertLess(score, 35.0)
        self.assertTrue(any("Legal advisory" in reason for reason in reasons))

    def test_pure_construction_tender_scores_low(self):
        score, reasons, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Railway construction works and civil engineering package",
                summary="Design and construction work for a new railway section with tunnels and drainage.",
                cpv_codes=["45000000", "45200000", "45233100"],
                organization_name="Rail Infrastructure Authority",
            ),
            None,
        )
        self.assertLess(score, 35.0)
        self.assertTrue(any("Construction works" in reason for reason in reasons))

    def test_construction_plus_document_management_is_not_incorrectly_rejected(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Construction project document management system",
                summary="Implementation of a document management platform for infrastructure programme controls and approvals.",
                cpv_codes=["45000000", "48311100", "72512000"],
                organization_name="Transport Authority",
            ),
            None,
        )
        self.assertGreaterEqual(score, 35.0)

    def test_hardware_only_tender_scores_low(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Procurement of hardware devices and printers",
                summary="Supply of hardware equipment and devices without software implementation.",
                cpv_codes=["30000000", "30200000"],
                organization_name="Procurement Office",
            ),
            None,
        )
        self.assertLess(score, 35.0)

    def test_it_consulting_can_score_medium_or_high(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="IT consulting, software development and internet support",
                summary="ERP, SAP and software integration support for enterprise systems.",
                cpv_codes=["72222300", "72230000", "72227000"],
                organization_name="City of Munich IT Department",
            ),
            None,
        )
        self.assertGreaterEqual(score, 65.0)

    def test_multilingual_notice_scores_via_cpv_metadata(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Lengyelország – Gyógyászati információs rendszerek",
                summary="Przyspieszenie procesów transformacji cyfrowej ochrony zdrowia.",
                cpv_codes=["48814000", "48180000", "72263000", "72227000"],
                organization_name="Szpital Specjalistyczny",
            ),
            None,
        )
        self.assertGreaterEqual(score, 50.0)

    def test_strong_cpv_boosts_score(self):
        high_score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Software maintenance and custom application support",
                summary="Application support and enhancement services.",
                cpv_codes=["72230000", "72267100"],
            ),
            None,
        )
        low_score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Specialist support services",
                summary="General advisory support.",
                cpv_codes=["79410000"],
            ),
            None,
        )
        self.assertGreater(high_score, low_score)

    def test_irrelevant_cpv_penalizes_score(self):
        score, _, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Security guarding services",
                summary="Guard services for public buildings.",
                cpv_codes=["79710000", "79713000"],
            ),
            None,
        )
        self.assertLess(score, 35.0)

    def test_expired_and_closing_soon_status_calculation(self):
        expired = service._ted_closing_status(self.fixed_now - service.timedelta(days=1), now=self.fixed_now)
        closing_soon = service._ted_closing_status(self.fixed_now + service.timedelta(days=7), now=self.fixed_now)
        open_status = service._ted_closing_status(self.fixed_now + service.timedelta(days=30), now=self.fixed_now)
        unknown = service._ted_closing_status(None, now=self.fixed_now)
        self.assertEqual(expired, "expired")
        self.assertEqual(closing_soon, "closing_soon")
        self.assertEqual(open_status, "open")
        self.assertEqual(unknown, "unknown")

    def test_relevance_bands(self):
        self.assertEqual(service._ted_relevance_band(88.0), "strong")
        self.assertEqual(service._ted_relevance_band(70.0), "good")
        self.assertEqual(service._ted_relevance_band(55.0), "possible")
        self.assertEqual(service._ted_relevance_band(40.0), "weak")
        self.assertEqual(service._ted_relevance_band(10.0), "low")

    def test_reason_generation_splits_positive_and_negative_signals(self):
        _, reasons, _ = service._calculate_preliminary_relevance(
            self._make_ted_candidate(
                title="Legal advisory for workflow software platform",
                summary="Workflow software implementation with legal review support.",
                cpv_codes=["72230000", "79111000"],
            ),
            None,
        )
        positives, negatives = service._split_relevance_reasons(reasons)
        self.assertTrue(positives)
        self.assertTrue(negatives)

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_ted_scan_failure_is_persisted_as_controlled_connector_error(self, mock_search_notices: Mock):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        mock_search_notices.side_effect = service.TedApiError(
            "TED rejected the search request because the connector field configuration is invalid.",
            provider_message="Parameter 'fields' contains unsupported value (supported values are: field-1, field-2, field-3)",
            http_status=400,
            provider_error_code="BAD_REQUEST",
            request_id="ted-request-1",
        )

        with self.assertRaises(Exception) as captured:
            service.run_connector_scan(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                AugmisBusinessConnectorScanRequest(run_type="manual"),
            )

        self.assertIn("TED rejected the search request because the connector field configuration is invalid.", str(captured.exception))
        run = (
            self.db.query(BusinessDevelopmentConnectorRun)
            .filter(BusinessDevelopmentConnectorRun.connector_id == connector.id)
            .order_by(BusinessDevelopmentConnectorRun.created_at.desc())
            .first()
        )
        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(run.status, "failed")
        self.assertEqual(
            run.error_summary,
            "TED rejected the search request because the connector field configuration is invalid.",
        )
        self.assertEqual(
            connector_row.last_error_message,
            "TED rejected the search request because the connector field configuration is invalid.",
        )
        self.assertEqual(run.run_metadata_json["provider_error"]["provider_http_status"], 400)
        self.assertEqual(run.run_metadata_json["provider_error"]["provider_error_code"], "BAD_REQUEST")
        self.assertEqual(run.run_metadata_json["provider_error"]["request_id"], "ted-request-1")
        self.assertNotIn("supported values are", connector_row.last_error_message)

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_ted_failure_preserves_previous_success_timestamp(self, mock_search_notices: Mock):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        mock_search_notices.return_value = {"total": 0, "items": [], "invalid_items": 0, "raw": {}}
        first = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["connector"]
        successful_last_success_at = first["last_success_at"]

        mock_search_notices.side_effect = service.TedApiError(
            "TED rejected the search request.",
            provider_message="Query syntax invalid near FT",
            http_status=400,
        )
        with self.assertRaises(Exception):
            service.run_connector_scan(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                AugmisBusinessConnectorScanRequest(run_type="manual"),
            )

        connector_row = service._require_connector(self.db, "TENANT-1", connector.id)
        self.assertEqual(service._serialize_datetime(connector_row.last_success_at), successful_last_success_at)


if __name__ == "__main__":
    unittest.main()
