from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorRun,
    BusinessDevelopmentDiscoveredOpportunity,
    BusinessDevelopmentDiscoveryTranslation,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.models.augmis_business_models import AugmisBusinessConnectorScanRequest
from app.services import augmis_business_listener_service as service


class TedConnectorPipelineTest(unittest.TestCase):
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
                BusinessDevelopmentConnector.__table__,
                BusinessDevelopmentConnectorRun.__table__,
                BusinessDevelopmentDiscoveredOpportunity.__table__,
                BusinessDevelopmentDiscoveryTranslation.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.original_now = service._now
        service._now = lambda: datetime(2026, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
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
        self.db.add_all(
            [
                Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"),
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
                    industries_json=["Public Procurement"],
                    keywords_json=["workflow", "dashboard", "portal"],
                    reusable_capabilities_json=["records management", "approval workflows"],
                    confidentiality_safe_summary="Reusable workflow experience.",
                    status="active",
                    created_by="USER-1",
                    updated_at=service._now(),
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        service._now = self.original_now
        self.db.close()

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_ted_connector_scan_creates_discovery_and_repeat_scan_dedupes(self, mock_search_notices):
        mock_search_notices.return_value = {
            "total": 1,
            "items": [
                service.TedNotice(
                    publication_number="123456-2026",
                    notice_identifier="TEN-0001",
                    notice_version="1",
                    title="Workflow automation and reporting system",
                    buyer_name="City Council",
                    buyer_country="DEU",
                    place_of_performance=["DEU"],
                    publication_date=datetime(2026, 8, 8, tzinfo=timezone.utc),
                    deadline=datetime(2026, 8, 30, tzinfo=timezone.utc),
                    notice_type="cn-standard",
                    procedure_type="open",
                    contract_nature="services",
                    cpv_codes=["72262000", "48311100"],
                    estimated_value=95000.0,
                    estimated_currency="EUR",
                    official_language="ENG",
                    official_notice_url="https://ted.europa.eu/en/notice/123456-2026/html",
                    summary="Build workflow automation and analytics system",
                    lot_summary=None,
                    raw_notice={"publication-number": ["123456-2026"]},
                )
            ],
            "invalid_items": 0,
            "raw": {},
        }
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)

        first = service.run_connector_scan(
            self.db, "TENANT-1", connector.id, self.current_user, AugmisBusinessConnectorScanRequest(run_type="manual")
        )["data"]["run"]
        second = service.run_connector_scan(
            self.db, "TENANT-1", connector.id, self.current_user, AugmisBusinessConnectorScanRequest(run_type="manual")
        )["data"]["run"]

        self.assertEqual(first["items_new"], 1)
        self.assertEqual(second["items_duplicate"], 1)
        discovery = self.db.query(BusinessDevelopmentDiscoveredOpportunity).filter_by(tenant_id="TENANT-1").first()
        self.assertIsNotNone(discovery)
        self.assertEqual(discovery.source_type, "public_procurement")
        self.assertEqual(discovery.source_name, "TED")
        self.assertEqual(discovery.organization_name, "City Council")

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_ted_notice_version_refreshes_existing_discovery(self, mock_search_notices):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        mock_search_notices.return_value = {
            "total": 1,
            "items": [
                service.TedNotice(
                    publication_number="123456-2026",
                    notice_identifier="TEN-0001",
                    notice_version="1",
                    title="Workflow automation system",
                    buyer_name="City Council",
                    buyer_country="DEU",
                    place_of_performance=["DEU"],
                    publication_date=datetime(2026, 8, 8, tzinfo=timezone.utc),
                    deadline=datetime(2026, 8, 30, tzinfo=timezone.utc),
                    notice_type="cn-standard",
                    procedure_type="open",
                    contract_nature="services",
                    cpv_codes=["72262000"],
                    estimated_value=50000.0,
                    estimated_currency="EUR",
                    official_language="ENG",
                    official_notice_url="https://ted.europa.eu/en/notice/123456-2026/html",
                    summary="Original summary",
                    lot_summary=None,
                    raw_notice={"publication-number": ["123456-2026"]},
                )
            ],
            "invalid_items": 0,
            "raw": {},
        }
        service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)
        mock_search_notices.return_value = {
            "total": 1,
            "items": [
                service.TedNotice(
                    publication_number="123456-2026",
                    notice_identifier="TEN-0001",
                    notice_version="2",
                    title="Workflow automation system updated",
                    buyer_name="City Council",
                    buyer_country="DEU",
                    place_of_performance=["DEU"],
                    publication_date=datetime(2026, 8, 8, tzinfo=timezone.utc),
                    deadline=datetime(2026, 9, 2, tzinfo=timezone.utc),
                    notice_type="cn-standard",
                    procedure_type="open",
                    contract_nature="services",
                    cpv_codes=["72262000"],
                    estimated_value=65000.0,
                    estimated_currency="EUR",
                    official_language="ENG",
                    official_notice_url="https://ted.europa.eu/en/notice/123456-2026/html",
                    summary="Updated summary",
                    lot_summary=None,
                    raw_notice={"publication-number": ["123456-2026"]},
                )
            ],
            "invalid_items": 0,
            "raw": {},
        }
        service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)
        discovery = self.db.query(BusinessDevelopmentDiscoveredOpportunity).filter_by(tenant_id="TENANT-1").first()
        self.assertEqual(discovery.title, "Workflow automation system updated")
        self.assertEqual(discovery.budget_max, 65000.0)
        self.assertEqual(discovery.raw_content_json.get("notice_version"), "2")

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_ted_discovery_can_be_imported_as_opportunity(self, mock_search_notices):
        mock_search_notices.return_value = {
            "total": 1,
            "items": [
                service.TedNotice(
                    publication_number="123456-2026",
                    notice_identifier="TEN-0001",
                    notice_version="1",
                    title="Workflow automation and reporting system",
                    buyer_name=None,
                    buyer_country="DEU",
                    place_of_performance=["DEU"],
                    publication_date=datetime(2026, 8, 8, tzinfo=timezone.utc),
                    deadline=None,
                    notice_type="cn-standard",
                    procedure_type="open",
                    contract_nature="services",
                    cpv_codes=[],
                    estimated_value=None,
                    estimated_currency=None,
                    official_language="ENG",
                    official_notice_url="https://ted.europa.eu/en/notice/123456-2026/html",
                    summary="Build workflow automation and analytics system",
                    lot_summary=None,
                    raw_notice={"publication-number": ["123456-2026"]},
                )
            ],
            "invalid_items": 0,
            "raw": {},
        }
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        service.run_connector_scan(self.db, "TENANT-1", connector.id, self.current_user)
        discovery = self.db.query(BusinessDevelopmentDiscoveredOpportunity).filter_by(tenant_id="TENANT-1").first()

        result = service.import_discovery_as_opportunity(
            self.db,
            "TENANT-1",
            discovery.id,
            self.current_user,
        )["data"]

        self.assertEqual(result["discovery"]["discovery_status"], "imported")
        self.assertEqual(result["opportunity"]["source_name"], "TED")
        self.assertEqual(result["opportunity"]["title"], "Workflow automation and reporting system")

    @patch("app.services.augmis_business_listener_service.TedSearchClient.search_notices")
    def test_zero_provider_results_are_distinguished_from_filtered_results(self, mock_search_notices):
        connector = service.ensure_ted_connector(self.db, "TENANT-1", self.current_user)
        mock_search_notices.return_value = {
            "total": 0,
            "items": [],
            "invalid_items": 0,
            "raw": {},
        }

        zero_provider_run = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]

        self.assertEqual(zero_provider_run["run_metadata_json"]["raw_results_fetched"], 0)
        self.assertEqual(zero_provider_run["run_metadata_json"]["accepted_candidates"], 0)
        self.assertEqual(zero_provider_run["items_filtered"], 0)

        mock_search_notices.return_value = {
            "total": 1,
            "items": [
                service.TedNotice(
                    publication_number="123456-2026",
                    notice_identifier="TEN-0002",
                    notice_version="1",
                    title="Laboratory hardware supply contract",
                    buyer_name="City Council",
                    buyer_country="DEU",
                    place_of_performance=["DEU"],
                    publication_date=datetime(2026, 8, 8, tzinfo=timezone.utc),
                    deadline=datetime(2026, 8, 30, tzinfo=timezone.utc),
                    notice_type="cn-standard",
                    procedure_type="open",
                    contract_nature="supplies",
                    cpv_codes=["48170000"],
                    estimated_value=95000.0,
                    estimated_currency="EUR",
                    official_language="ENG",
                    official_notice_url="https://ted.europa.eu/en/notice/123456-2026/html",
                    summary="Supply and installation of laboratory hardware units",
                    lot_summary=None,
                    raw_notice={"publication-number": ["123456-2026"]},
                )
            ],
            "invalid_items": 0,
            "raw": {},
        }

        filtered_run = service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]["run"]

        self.assertGreaterEqual(filtered_run["run_metadata_json"]["raw_results_fetched"], 1)
        self.assertEqual(filtered_run["run_metadata_json"]["accepted_candidates"], 1)
        self.assertGreaterEqual(filtered_run["items_filtered"], 1)


if __name__ == "__main__":
    unittest.main()
