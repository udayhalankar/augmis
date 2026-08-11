from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
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
    BusinessDevelopmentWebDomain,
    BusinessDevelopmentWebFrontier,
    BusinessDevelopmentWebPage,
    BusinessDevelopmentWebSeed,
    Tenant,
    User,
)
from app.models.augmis_business_models import (
    AugmisBusinessConnectorScanRequest,
    AugmisBusinessWebSeedCreateRequest,
)
from app.services import augmis_business_listener_service as listener_service
from app.services import augmis_business_independent_discovery_service as discovery_service
from app.services.augmis_business_web_fetcher import SafeWebFetchError


class AugmisBusinessIndependentDiscoveryServiceTest(unittest.TestCase):
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
                BusinessDevelopmentWebSeed.__table__,
                BusinessDevelopmentWebDomain.__table__,
                BusinessDevelopmentWebFrontier.__table__,
                BusinessDevelopmentWebPage.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 10, 9, 0, 0, tzinfo=timezone.utc)
        self.original_listener_now = listener_service._now
        self.original_discovery_now = discovery_service._now
        self.original_discovery_sleep = discovery_service._sleep
        listener_service._now = lambda: self.fixed_now
        discovery_service._now = lambda: self.fixed_now
        discovery_service._sleep = lambda seconds: self._advance_now(seconds)
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
                    name="Workflow Delivery",
                    category="Applications",
                    description="Workflow and dashboard experience.",
                    business_problems_json=[],
                    features_json=["Approvals", "Dashboards"],
                    technologies_json=["React", "FastAPI"],
                    industries_json=["Utilities"],
                    keywords_json=["workflow automation", "custom software", "document management"],
                    reusable_capabilities_json=["approval workflows"],
                    confidentiality_safe_summary="Workflow delivery experience.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        listener_service._now = self.original_listener_now
        discovery_service._now = self.original_discovery_now
        discovery_service._sleep = self.original_discovery_sleep
        self.db.close()

    def _advance_now(self, seconds: float) -> None:
        self.fixed_now = self.fixed_now + timedelta(seconds=seconds)

    def _allow_all_robots(self, domain: str) -> dict[str, object]:
        return {
            "url": f"https://{domain}/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }

    def _create_connector(self, **config):
        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        merged = dict(connector.configuration_json or {})
        merged.update(config)
        connector.configuration_json = merged
        self.db.commit()
        self.db.refresh(connector)
        return connector

    def _create_isolated_connector(self, *, name: str, **config):
        profile = listener_service.ensure_default_search_profile(self.db, "TENANT-1", self.current_user)
        connector = BusinessDevelopmentConnector(
            id=f"BD-CNX-TEST-{self.db.query(BusinessDevelopmentConnector).count() + 1}",
            tenant_id="TENANT-1",
            search_profile_id=profile.id,
            connector_type=discovery_service.INDEPENDENT_WEB_CONNECTOR_TYPE,
            name=name,
            source_category="company_source",
            status="ready",
            enabled=True,
            schedule_enabled=False,
            schedule_expression=None,
            schedule_type="manual",
            schedule_timezone="UTC",
            configuration_json={
                "maximum_seeds_per_run": 5,
                "maximum_domains_per_run": 5,
                "maximum_pages_per_domain": 25,
                "maximum_total_pages_per_run": 100,
                "maximum_depth": 2,
                "request_timeout_seconds": 15,
                "per_domain_delay_seconds": 2,
                "recrawl_interval_hours": 168,
                "allowed_domain_mode": "approved_only",
                "max_fetch_bytes": 2_000_000,
                "max_extracted_text_chars": 40000,
                "maximum_links_per_page": 40,
                "maximum_run_duration_seconds": 180,
                **config,
            },
            search_criteria_json={},
            capability_flags_json={
                "mode": "Production",
                "provider_label": "AUGMIS Internal",
                "credential_state": "none_required",
            },
            created_by="USER-1",
            updated_at=self.fixed_now,
        )
        self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)
        return connector

    def _create_seed(
        self,
        connector,
        *,
        name: str,
        seed_url: str,
        priority: int = 50,
        max_depth: int = 3,
        max_pages: int = 10,
        next_crawl_at: datetime | None = None,
    ):
        result = discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name=name,
                seed_url=seed_url,
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=max_depth,
                max_pages=max_pages,
                crawl_frequency="weekly",
                priority=priority,
            ),
        )
        seed = self.db.query(BusinessDevelopmentWebSeed).filter(BusinessDevelopmentWebSeed.id == result["data"]["id"]).first()
        assert seed is not None
        if next_crawl_at is not None:
            seed.next_crawl_at = next_crawl_at
            self.db.commit()
            self.db.refresh(seed)
        return seed

    def _run_scan(self, connector):
        return listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_independent_connector_creates_discovery_without_external_search_credentials(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        payloads = {
            "https://buyer.example/rfp/workflow": {
                "url": "https://buyer.example/rfp/workflow",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html>
                      <head>
                        <title>Workflow Automation RFP</title>
                        <meta property="og:site_name" content="City Utilities Authority" />
                      </head>
                      <body>
                        <h1>Workflow Automation RFP</h1>
                        <p>Request for proposal for workflow automation and document management system.</p>
                        <p>Deadline: 2026-08-25</p>
                        <p>Budget: USD 120000</p>
                        <p>Procurement contact: procurement@buyer.example</p>
                        <a href="/contact">Contact Us</a>
                      </body>
                    </html>
                """,
                "bytes_read": 620,
            },
            "https://buyer.example/contact": {
                "url": "https://buyer.example/contact",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html><head><title>Contact Us</title></head><body>
                    <h1>Contact Us</h1><p>Reach procurement@buyer.example for questions.</p>
                    </body></html>
                """,
                "bytes_read": 180,
            },
        }
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: payloads[url]

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Buyer RFP Seed",
                seed_url="https://buyer.example/rfp/workflow",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=0,
                max_pages=10,
                crawl_frequency="weekly",
                priority=80,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["status"], "completed")
        self.assertEqual(result["run"]["run_metadata_json"]["provider"], "augmis_internal")
        self.assertEqual(len(result["discoveries"]), 1)
        self.assertEqual(result["discoveries"][0]["source_name"], "AUGMIS Web")
        self.assertEqual(result["discoveries"][0]["display_source"], "AUGMIS Web")
        self.assertEqual(result["discoveries"][0]["source_provider_key"], "augmis_internal")
        self.assertEqual(result["discoveries"][0]["source_type"], "public_procurement")
        self.assertEqual(
            result["discoveries"][0]["raw_content_json"]["provider"],
            "augmis_internal",
        )
        self.assertIn("procurement@buyer.example", str(result["discoveries"][0]["raw_content_json"]))
        self.assertEqual(result["run"]["run_metadata_json"]["pages_attempted"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_pages"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["candidates_created"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["candidates_accepted"], 1)
        discovery_rows = self.db.query(BusinessDevelopmentDiscoveredOpportunity).all()
        self.assertEqual(len(discovery_rows), 1)
        page_rows = self.db.query(BusinessDevelopmentWebPage).all()
        self.assertEqual(len(page_rows), 1)

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_robots_denied_url_is_not_fetched(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nDisallow: /rfp",
            "bytes_read": 26,
        }
        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Denied Seed",
                seed_url="https://buyer.example/rfp/workflow",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=50,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["status"], "completed")
        self.assertEqual(result["run"]["items_new"], 0)
        self.assertEqual(result["run"]["run_metadata_json"]["robots_denied"], 1)
        mock_fetch_page.assert_not_called()
        frontier = self.db.query(BusinessDevelopmentWebFrontier).first()
        self.assertIsNotNone(frontier)
        self.assertEqual(frontier.status, "robots_denied")
        domain = self.db.query(BusinessDevelopmentWebDomain).first()
        self.assertIsNotNone(domain)
        self.assertEqual(domain.robots_status, "denied")

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_procurement_portal_page_is_persisted_with_exclusion_diagnostics_not_discovery(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://eprocure.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        mock_fetch_page.return_value = {
            "url": "https://eprocure.example/app?service=home",
            "status_code": 200,
            "content_type": "text/html",
            "body": """
                <html>
                  <head>
                    <title>Government eProcurement System</title>
                  </head>
                  <body>
                    <h1>ePublishing System, Government of India eProcurement System</h1>
                    <p>Expression of Interest, active tenders, standard bidding documents and published bids.</p>
                    <p>Browse tenders and bid schedule information.</p>
                  </body>
                </html>
            """,
            "bytes_read": 420,
        }

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Portal Seed",
                seed_url="https://eprocure.example/app?service=home",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=50,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["items_found"], 0)
        self.assertEqual(result["run"]["items_filtered"], 0)
        self.assertEqual(len(result["discoveries"]), 0)
        self.assertEqual(result["run"]["run_metadata_json"]["listing_pages"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_pages"], 0)
        self.assertEqual(
            result["run"]["run_metadata_json"]["candidate_exclusion_reason_counts"]["page_type:procurement_list"],
            1,
        )
        page_row = self.db.query(BusinessDevelopmentWebPage).first()
        self.assertIsNotNone(page_row)
        assert page_row is not None
        self.assertEqual(page_row.page_type, "procurement_list")
        self.assertFalse(page_row.source_metadata_json["candidate_visibility"]["eligible"])
        self.assertIn("page_type:procurement_list", page_row.source_metadata_json["candidate_visibility"]["reason_codes"])

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_independent_procurement_detail_gets_source_aware_relevance_and_run_diagnostics(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        payloads = {
            "https://buyer.example/tenders/workflow-2026": {
                "url": "https://buyer.example/tenders/workflow-2026",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html>
                      <head>
                        <title>Workflow Automation RFP Tender ID WA-2026-77</title>
                        <meta property="og:site_name" content="City Utilities Authority" />
                      </head>
                      <body>
                        <h1>Workflow Automation RFP</h1>
                        <p>Request for proposal for workflow automation and document management system.</p>
                        <p>Reference Number: WA-2026-77</p>
                        <p>Scope of work includes portal integration, dashboards, records management, and analytics.</p>
                        <p>Closing Date: 25/08/2026</p>
                        <p>Budget: USD 120000</p>
                        <p>Procurement contact: procurement@buyer.example</p>
                        <a href="/submit">Submit proposal</a>
                      </body>
                    </html>
                """,
                "bytes_read": 860,
            },
            "https://buyer.example/submit": {
                "url": "https://buyer.example/submit",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html><head><title>Submit Proposal</title></head><body>
                    <h1>Submit Proposal</h1><p>Portal submission page.</p>
                    </body></html>
                """,
                "bytes_read": 150,
            },
        }
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: payloads[url]

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Detail Seed",
                seed_url="https://buyer.example/tenders/workflow-2026",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=80,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["items_new"], 1)
        self.assertEqual(result["run"]["items_filtered"], 0)
        self.assertEqual(len(result["discoveries"]), 1)
        discovery = result["discoveries"][0]
        self.assertGreaterEqual(discovery["preliminary_relevance_score"], 25.0)
        self.assertEqual(discovery["raw_content_json"]["crawler_diagnostics"]["discovery_status"], "new")
        self.assertIn("accepted_preliminary_relevance", discovery["raw_content_json"]["crawler_diagnostics"]["reason_codes"])
        self.assertTrue(
            any(
                "Independent crawl captured a procurement-detail page" in reason
                for reason in discovery["relevance_reasons_json"]
            )
        )
        self.assertTrue(result["run"]["run_metadata_json"]["candidate_outcomes"])

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_stale_session_page_is_classified_and_not_imported(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        mock_fetch_page.return_value = {
            "url": "https://buyer.example/eprocure/app?session=T",
            "status_code": 200,
            "content_type": "text/html",
            "body": """
                <html>
                  <head><title>Stale Session</title></head>
                  <body>
                    <h1>Stale Session</h1>
                    <p>Your session has expired. Return to the procurement portal home page.</p>
                  </body>
                </html>
            """,
            "bytes_read": 180,
        }

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Stale Session Seed",
                seed_url="https://buyer.example/eprocure/app?session=T",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=50,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["items_found"], 0)
        self.assertEqual(len(result["discoveries"]), 0)
        self.assertEqual(result["run"]["run_metadata_json"]["stale_or_error_pages"], 1)
        page_row = self.db.query(BusinessDevelopmentWebPage).first()
        self.assertIsNotNone(page_row)
        assert page_row is not None
        self.assertEqual(page_row.page_type, "stale_session")
        self.assertIn(
            "page_type:stale_session",
            page_row.source_metadata_json["candidate_visibility"]["reason_codes"],
        )

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_cross_domain_reference_is_registered_without_deep_crawl(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        mock_fetch_page.return_value = {
            "url": "https://buyer.example/rfp/workflow",
            "status_code": 200,
            "content_type": "text/html",
            "body": """
                <html>
                  <head><title>Workflow Automation RFP</title></head>
                  <body>
                    <h1>Workflow Automation RFP</h1>
                    <p>Request for proposal for workflow automation and document management system.</p>
                    <a href="https://get.adobe.com/reader/">PDF reader help</a>
                  </body>
                </html>
            """,
            "bytes_read": 260,
        }

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Cross Domain Seed",
                seed_url="https://buyer.example/rfp/workflow",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=80,
            ),
        )

        listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )

        domain_rows = self.db.query(BusinessDevelopmentWebDomain).order_by(BusinessDevelopmentWebDomain.domain.asc()).all()
        frontier_rows = self.db.query(BusinessDevelopmentWebFrontier).order_by(BusinessDevelopmentWebFrontier.domain.asc()).all()
        self.assertEqual(len(domain_rows), 2)
        referenced_domain = next(row for row in domain_rows if row.domain == "get.adobe.com")
        self.assertEqual(referenced_domain.approval_status, "pending_review")
        self.assertEqual([row.domain for row in frontier_rows], ["buyer.example"])

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_listing_page_detail_link_counters_are_recorded(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        payloads = {
            "https://buyer.example/procurement/list": {
                "url": "https://buyer.example/procurement/list",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html>
                      <head><title>Active Tenders</title></head>
                      <body>
                        <h1>Active Tenders</h1>
                        <p>Browse tenders and published bids.</p>
                        <a href="/tenders/workflow-rfp-2026">Workflow Automation RFP 2026</a>
                      </body>
                    </html>
                """,
                "bytes_read": 220,
            },
            "https://buyer.example/tenders/workflow-rfp-2026": {
                "url": "https://buyer.example/tenders/workflow-rfp-2026",
                "status_code": 200,
                "content_type": "text/html",
                "body": """
                    <html>
                      <head>
                        <title>Workflow Automation RFP 2026</title>
                        <meta property="og:site_name" content="City Utilities Authority" />
                      </head>
                      <body>
                        <h1>Workflow Automation RFP 2026</h1>
                        <p>Request for proposal for workflow automation and document management system.</p>
                        <p>City Utilities Authority invites proposals.</p>
                        <p>Reference Number: WF-2026-09</p>
                        <p>Closing Date: 25/08/2026</p>
                        <a href="/tenders/workflow-rfp-2026/submit">Submit proposal</a>
                      </body>
                    </html>
                """,
                "bytes_read": 260,
            },
            "https://buyer.example/tenders/workflow-rfp-2026/submit": {
                "url": "https://buyer.example/tenders/workflow-rfp-2026/submit",
                "status_code": 200,
                "content_type": "text/html",
                "body": "<html><head><title>Submit Proposal</title></head><body><h1>Submit Proposal</h1></body></html>",
                "bytes_read": 96,
            },
        }
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: payloads[url]

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Listing Seed",
                seed_url="https://buyer.example/procurement/list",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=2,
                max_pages=10,
                crawl_frequency="weekly",
                priority=70,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]

        self.assertEqual(result["run"]["items_new"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["listing_pages"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_links_discovered"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_links_queued"], 1)
        discoveries = (
            self.db.query(BusinessDevelopmentDiscoveredOpportunity)
            .filter(BusinessDevelopmentDiscoveredOpportunity.tenant_id == "TENANT-1")
            .all()
        )
        self.assertEqual(len(discoveries), 1)
        self.assertEqual(discoveries[0].title, "Workflow Automation RFP 2026")

    def test_same_domain_session_reused_and_cross_domain_isolated(self):
        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        engine = discovery_service.IndependentWebDiscoveryEngine(self.db, connector, None)
        first = engine._session_for_domain("buyer.example")
        second = engine._session_for_domain("buyer.example")
        third = engine._session_for_domain("other.example")
        self.assertIs(first, second)
        self.assertIsNot(first, third)
        engine._close_sessions()

    def test_session_bound_url_detection_only_flags_tokenized_session_links(self):
        durable = discovery_service._session_bound_url_reasons("https://eprocure.example/app?page=list&session=T")
        transient = discovery_service._session_bound_url_reasons(
            "https://eprocure.example/app?page=detail&jsessionid=ABCDEF1234567890"
        )
        self.assertEqual(durable, [])
        self.assertIn("query_jsessionid", transient)

    def test_retry_delay_is_bounded_for_429_5xx_and_timeout(self):
        self.assertEqual(
            discovery_service._retry_delay_for_diagnostic({"error_code": "HTTP_429", "retryable": True, "retry_after": "120"}, attempt_number=1),
            timedelta(seconds=120),
        )
        self.assertEqual(
            discovery_service._retry_delay_for_diagnostic({"error_code": "HTTP_5XX", "retryable": True}, attempt_number=2),
            timedelta(minutes=10),
        )
        self.assertEqual(
            discovery_service._retry_delay_for_diagnostic({"error_code": "READ_TIMEOUT", "retryable": True}, attempt_number=3),
            timedelta(minutes=30),
        )
        self.assertIsNone(
            discovery_service._retry_delay_for_diagnostic({"error_code": "HTTP_403", "retryable": False}, attempt_number=1)
        )

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_relative_html_entity_url_is_normalized_and_invalid_links_ignored(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        mock_fetch_page.return_value = {
            "url": "https://buyer.example/tenders",
            "status_code": 200,
            "content_type": "text/html",
            "body": """
                <html>
                  <head><title>Active Tenders</title></head>
                  <body>
                    <a href="/notice?id=44&amp;mode=view">Open Tender</a>
                    <a href="javascript:void(0)">Ignore JS</a>
                    <a href="mailto:buyer@example.com">Ignore Mail</a>
                    <a href="#fragment">Ignore Anchor</a>
                  </body>
                </html>
            """,
            "bytes_read": 220,
        }

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="HTML Entity Seed",
                seed_url="https://buyer.example/tenders",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=70,
            ),
        )

        listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )
        frontier_rows = self.db.query(BusinessDevelopmentWebFrontier).order_by(BusinessDevelopmentWebFrontier.depth.asc()).all()
        self.assertEqual(len(frontier_rows), 2)
        self.assertEqual(frontier_rows[1].canonical_url, "https://buyer.example/notice?id=44&mode=view")

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_failure_diagnostics_are_persisted_on_frontier(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = {
            "url": "https://buyer.example/robots.txt",
            "status_code": 200,
            "content_type": "text/plain",
            "body": "User-agent: *\nAllow: /",
            "bytes_read": 18,
        }
        mock_fetch_page.side_effect = SafeWebFetchError(
            "Source page returned HTTP 403.",
            code="HTTP_403",
            retryable=False,
            http_status=403,
            final_url="https://buyer.example/forbidden",
        )

        connector = listener_service.ensure_independent_web_connector(self.db, "TENANT-1", self.current_user)
        discovery_service.create_web_seed(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessWebSeedCreateRequest(
                name="Forbidden Seed",
                seed_url="https://buyer.example/forbidden",
                seed_type="url",
                crawl_scope="same_domain",
                max_depth=1,
                max_pages=10,
                crawl_frequency="weekly",
                priority=50,
            ),
        )

        result = listener_service.run_connector_scan(
            self.db,
            "TENANT-1",
            connector.id,
            self.current_user,
            AugmisBusinessConnectorScanRequest(run_type="manual"),
        )["data"]
        frontier = self.db.query(BusinessDevelopmentWebFrontier).first()
        self.assertIsNotNone(frontier)
        assert frontier is not None
        self.assertEqual(frontier.error_code, "HTTP_403")
        self.assertFalse(frontier.diagnostic_json["retryable"])
        self.assertEqual(frontier.diagnostic_json["http_status"], 403)
        self.assertEqual(result["run"]["run_metadata_json"]["fetch_failure_counts"]["HTTP_403"], 1)

    @patch("app.services.augmis_business_independent_discovery_service._sleep")
    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_same_domain_pages_continue_with_delay_inside_one_run(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
        mock_sleep,
    ):
        del mock_validate_url
        mock_fetch_text.return_value = self._allow_all_robots("example-procurement.test")
        mock_sleep.side_effect = lambda seconds: self._advance_now(seconds)
        payloads = {
            "https://example-procurement.test/root": """
                <html><head><title>Procurement Portal</title></head><body>
                <a href="/page1">Page 1</a>
                </body></html>
            """,
            "https://example-procurement.test/page1": """
                <html><head><title>Tender Page 1</title></head><body>
                <a href="/page2">Page 2</a>
                </body></html>
            """,
            "https://example-procurement.test/page2": """
                <html><head><title>Tender Page 2</title></head><body>
                <a href="/page3">Page 3</a>
                </body></html>
            """,
        }

        def fetch_page(url, policy, **kwargs):
            return {
                "url": url,
                "status_code": 200,
                "content_type": "text/html",
                "body": payloads[url],
                "bytes_read": len(payloads[url]),
            }

        mock_fetch_page.side_effect = fetch_page
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=3,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=60,
            per_domain_delay_seconds=2,
        )
        self._create_seed(connector, name="Same Domain Seed", seed_url="https://example-procurement.test/root")

        result = self._run_scan(connector)
        self.assertEqual(result["run"]["run_metadata_json"]["pages_fetched"], 3)
        self.assertGreaterEqual(mock_sleep.call_count, 2)

    @patch("app.services.augmis_business_independent_discovery_service._sleep")
    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_maximum_pages_per_domain_is_enforced_per_run_not_lifetime(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
        mock_sleep,
    ):
        del mock_validate_url
        mock_sleep.side_effect = lambda seconds: self._advance_now(seconds)
        domain = "history.example"
        mock_fetch_text.return_value = self._allow_all_robots(domain)
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: {
            "url": url,
            "status_code": 200,
            "content_type": "text/html",
            "body": f"<html><head><title>Tender {url}</title></head><body>Tender detail</body></html>",
            "bytes_read": 120,
        }
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=60,
        )
        seed = self._create_seed(
            connector,
            name="History Seed",
            seed_url="https://history.example/root",
            next_crawl_at=self.fixed_now + timedelta(days=1),
        )
        domain_row = discovery_service._ensure_domain(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain=domain,
            source="seed",
            found_from_url=seed.seed_url,
            found_context=seed.name,
            default_approval="approved",
        )
        for index in range(100):
            self.db.add(
                BusinessDevelopmentWebPage(
                    id=f"PAGE-HIST-{index}",
                    tenant_id="TENANT-1",
                    connector_id=connector.id,
                    seed_id=seed.id,
                    domain_id=domain_row.id,
                    url=f"https://{domain}/historical-{index}",
                    canonical_url=f"https://{domain}/historical-{index}",
                    domain=domain,
                    page_type="tender",
                    title=f"Historical {index}",
                    plain_text="Historical page",
                    safe_html="<html></html>",
                    first_seen_at=self.fixed_now - timedelta(days=30),
                    last_seen_at=self.fixed_now - timedelta(days=30),
                    last_changed_at=self.fixed_now - timedelta(days=30),
                )
            )
        for index in range(5):
            discovery_service._enqueue_frontier_url(
                self.db,
                tenant_id="TENANT-1",
                connector_id=connector.id,
                seed=seed,
                domain_row=domain_row,
                url=f"https://{domain}/new-{index}",
                parent_url=seed.seed_url,
                anchor_text=f"New {index}",
                context="Queued for current run",
                depth=1,
                priority=80 - index,
            )
        self.db.commit()

        engine = discovery_service.IndependentWebDiscoveryEngine(self.db, connector, None)
        discoveries, metrics = engine.run()
        del discoveries
        self.assertEqual(metrics["pages_fetched"], 5)
        blocked = self.db.query(BusinessDevelopmentWebFrontier).filter(BusinessDevelopmentWebFrontier.error_code == "DOMAIN_PAGE_LIMIT").count()
        self.assertEqual(blocked, 0)

    @patch("app.services.augmis_business_independent_discovery_service._sleep")
    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_maximum_domains_per_run_allows_multiple_pages_on_one_domain(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
        mock_sleep,
    ):
        del mock_validate_url
        mock_sleep.side_effect = lambda seconds: self._advance_now(seconds)
        mock_fetch_text.side_effect = lambda url, policy, **kwargs: self._allow_all_robots("domain-a.example" if "domain-a" in url else "domain-b.example")
        payloads = {
            "https://domain-a.example/root": "<html><head><title>Domain A Root</title></head><body><a href='/a-1'>A1</a></body></html>",
            "https://domain-a.example/a-1": "<html><head><title>Tender A1</title></head><body><a href='/a-2'>A2</a></body></html>",
            "https://domain-a.example/a-2": "<html><head><title>Tender A2</title></head><body>Done</body></html>",
            "https://domain-b.example/root": "<html><head><title>Domain B Root</title></head><body>Other domain</body></html>",
        }
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: {
            "url": url,
            "status_code": 200,
            "content_type": "text/html",
            "body": payloads[url],
            "bytes_read": len(payloads[url]),
        }
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=3,
            maximum_total_pages_per_run=4,
            maximum_run_duration_seconds=60,
            per_domain_delay_seconds=2,
        )
        self._create_seed(connector, name="Domain A Seed", seed_url="https://domain-a.example/root", priority=100)
        self._create_seed(connector, name="Domain B Seed", seed_url="https://domain-b.example/root", priority=10)

        result = self._run_scan(connector)
        self.assertEqual(result["run"]["run_metadata_json"]["pages_fetched"], 3)
        queued_b = (
            self.db.query(BusinessDevelopmentWebFrontier)
            .filter(
                BusinessDevelopmentWebFrontier.connector_id == connector.id,
                BusinessDevelopmentWebFrontier.domain == "domain-b.example",
                BusinessDevelopmentWebFrontier.status == "queued",
            )
            .count()
        )
        self.assertEqual(queued_b, 1)

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_session_bound_child_url_is_bootstrapped_via_parent_when_session_is_missing(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        domain = "buyer.example"
        mock_fetch_text.return_value = self._allow_all_robots(domain)
        child_url = "https://buyer.example/eprocure/app?page=detail&session=T&component=%24DirectLink0"
        parent_url = "https://buyer.example/eprocure/app?page=list&service=page"

        def fetch_page(url, policy, session=None, **kwargs):
            if url == parent_url:
                session.cookies.set("JSESSIONID", "anon-session")
                return {
                    "url": url,
                    "status_code": 200,
                    "content_type": "text/html",
                    "body": "<html><head><title>Public Tender List</title></head><body><a href='/noop'>noop</a></body></html>",
                    "bytes_read": 120,
                }
            if url == child_url:
                if session is None or session.cookies.get("JSESSIONID") != "anon-session":
                    raise SafeWebFetchError("Stale Session", code="HTTP_403", retryable=False, http_status=403, final_url=url)
                return {
                    "url": url,
                    "status_code": 200,
                    "content_type": "text/html",
                    "body": """
                        <html><head><title>Workflow Automation Tender WF-2026-88</title></head><body>
                        <h1>Workflow Automation Tender</h1>
                        <p>Request for proposal for workflow automation.</p>
                        <p>Reference Number: WF-2026-88</p>
                        <p>Closing Date: 25/08/2026</p>
                        </body></html>
                    """,
                    "bytes_read": 300,
                }
            raise AssertionError(url)

        mock_fetch_page.side_effect = fetch_page
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=60,
        )
        seed = self._create_seed(
            connector,
            name="Session Seed",
            seed_url=parent_url,
            next_crawl_at=self.fixed_now + timedelta(days=1),
        )
        domain_row = discovery_service._ensure_domain(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain=domain,
            source="seed",
            found_from_url=parent_url,
            found_context=seed.name,
            default_approval="approved",
        )
        discovery_service._enqueue_frontier_url(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain_row=domain_row,
            url=child_url,
            parent_url=parent_url,
            anchor_text="Open Tender",
            context="Session detail",
            depth=1,
            priority=90,
        )
        self.db.commit()

        engine = discovery_service.IndependentWebDiscoveryEngine(self.db, connector, None)
        discoveries, metrics = engine.run()
        self.assertEqual(metrics["pages_fetched"], 1)
        self.assertEqual(len(discoveries), 1)

    @patch("app.services.augmis_business_independent_discovery_service._sleep")
    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_pending_frontier_continues_on_second_run(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
        mock_sleep,
    ):
        del mock_validate_url
        mock_sleep.side_effect = lambda seconds: self._advance_now(seconds)
        domain = "continuation.example"
        mock_fetch_text.return_value = self._allow_all_robots(domain)
        payloads = {
            "https://continuation.example/root": "<html><head><title>Portal</title></head><body><a href='/page-1'>One</a><a href='/page-2'>Two</a></body></html>",
            "https://continuation.example/page-1": "<html><head><title>Tender One</title></head><body>Open</body></html>",
            "https://continuation.example/page-2": "<html><head><title>Tender Two</title></head><body>Open</body></html>",
        }
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: {
            "url": url,
            "status_code": 200,
            "content_type": "text/html",
            "body": payloads[url],
            "bytes_read": len(payloads[url]),
        }
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=10,
            maximum_total_pages_per_run=2,
            maximum_run_duration_seconds=60,
            per_domain_delay_seconds=2,
        )
        self._create_seed(connector, name="Continuation Seed", seed_url="https://continuation.example/root")

        first = self._run_scan(connector)
        queued_after_first = (
            self.db.query(BusinessDevelopmentWebFrontier)
            .filter(
                BusinessDevelopmentWebFrontier.connector_id == connector.id,
                BusinessDevelopmentWebFrontier.domain == domain,
                BusinessDevelopmentWebFrontier.status == "queued",
            )
            .count()
        )
        self.assertEqual(first["run"]["run_metadata_json"]["pages_fetched"], 2)
        self.assertGreaterEqual(queued_after_first, 1)

        self._advance_now(10)
        second = self._run_scan(connector)
        page_two = (
            self.db.query(BusinessDevelopmentWebFrontier)
            .filter(BusinessDevelopmentWebFrontier.connector_id == connector.id, BusinessDevelopmentWebFrontier.canonical_url == "https://continuation.example/page-2")
            .first()
        )
        assert page_two is not None
        self.assertEqual(second["run"]["run_metadata_json"]["pages_fetched"], 1)
        self.assertEqual(page_two.status, "fetched")

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_due_seed_requeues_only_its_fetched_root(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        domain = "recrawl.example"
        mock_fetch_text.return_value = self._allow_all_robots(domain)
        mock_fetch_page.return_value = {
            "url": "https://recrawl.example/root",
            "status_code": 200,
            "content_type": "text/html",
            "body": "<html><head><title>Portal Root</title></head><body>No children</body></html>",
            "bytes_read": 100,
        }
        connector = self._create_connector(
            maximum_domains_per_run=1,
            maximum_pages_per_domain=2,
            maximum_total_pages_per_run=2,
            maximum_run_duration_seconds=60,
        )
        seed = self._create_seed(connector, name="Recrawl Seed", seed_url="https://recrawl.example/root")
        domain_row = discovery_service._ensure_domain(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain=domain,
            source="seed",
            found_from_url=seed.seed_url,
            found_context=seed.name,
            default_approval="approved",
        )
        root = discovery_service._enqueue_frontier_url(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain_row=domain_row,
            url=seed.seed_url,
            parent_url=None,
            anchor_text=seed.name,
            context="Root",
            depth=0,
            priority=90,
        )
        child = discovery_service._enqueue_frontier_url(
            self.db,
            tenant_id="TENANT-1",
            connector_id=connector.id,
            seed=seed,
            domain_row=domain_row,
            url="https://recrawl.example/child",
            parent_url=seed.seed_url,
            anchor_text="Child",
            context="Child",
            depth=1,
            priority=50,
        )
        assert root is not None
        assert child is not None
        root.status = "fetched"
        root.next_fetch_at = self.fixed_now - timedelta(days=1)
        child.status = "fetched"
        child.next_fetch_at = self.fixed_now - timedelta(days=1)
        child.last_attempted_at = None
        seed.next_crawl_at = self.fixed_now
        self.db.commit()

        self._run_scan(connector)
        self.assertIsNotNone(root.last_attempted_at)
        self.assertIsNone(child.last_attempted_at)

    @patch("app.services.augmis_business_independent_discovery_service.validate_public_http_url")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_webpage")
    @patch("app.services.augmis_business_independent_discovery_service.fetch_public_text_resource")
    def test_run_status_distinguishes_exhausted_batch_duration_waiting_and_no_due_work(
        self,
        mock_fetch_text,
        mock_fetch_page,
        mock_validate_url,
    ):
        del mock_validate_url
        domain = "status.example"
        mock_fetch_text.return_value = self._allow_all_robots(domain)

        def create_status_connector(name: str, **config):
            return self._create_isolated_connector(name=name, **config)

        exhausted = create_status_connector(
            "Status Exhausted",
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=60,
        )
        self._create_seed(exhausted, name="Exhausted Seed", seed_url="https://status.example/exhausted")
        mock_fetch_page.side_effect = lambda url, policy, **kwargs: {
            "url": url,
            "status_code": 200,
            "content_type": "text/html",
            "body": "<html><head><title>Single Page</title></head><body>No links</body></html>",
            "bytes_read": 90,
        }
        exhausted_result = self._run_scan(exhausted)
        self.assertEqual(exhausted_result["run"]["run_metadata_json"]["status"], "frontier_exhausted")

        batch = create_status_connector(
            "Status Batch",
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=1,
            maximum_run_duration_seconds=60,
        )
        self._create_seed(batch, name="Batch Seed", seed_url="https://status.example/batch")

        def batch_fetch(url, policy, **kwargs):
            body = "<html><head><title>Batch Root</title></head><body><a href='/batch-child'>Child</a></body></html>"
            if "batch-child" in url:
                body = "<html><head><title>Batch Child</title></head><body>Open</body></html>"
            return {"url": url, "status_code": 200, "content_type": "text/html", "body": body, "bytes_read": len(body)}

        mock_fetch_page.side_effect = batch_fetch
        batch_result = self._run_scan(batch)
        self.assertEqual(batch_result["run"]["run_metadata_json"]["status"], "batch_limit_reached")

        duration = create_status_connector(
            "Status Duration",
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=30,
        )
        self._create_seed(duration, name="Duration Seed", seed_url="https://status.example/duration")

        def duration_fetch(url, policy, **kwargs):
            self._advance_now(31)
            body = "<html><head><title>Duration Root</title></head><body><a href='/duration-child'>Child</a></body></html>"
            if "duration-child" in url:
                body = "<html><head><title>Duration Child</title></head><body>Open</body></html>"
            return {"url": url, "status_code": 200, "content_type": "text/html", "body": body, "bytes_read": len(body)}

        mock_fetch_page.side_effect = duration_fetch
        duration_result = self._run_scan(duration)
        self.assertEqual(duration_result["run"]["run_metadata_json"]["status"], "run_duration_reached")

        waiting = create_status_connector(
            "Status Waiting",
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=30,
        )
        waiting_seed = self._create_seed(
            waiting,
            name="Waiting Seed",
            seed_url="https://status.example/waiting",
            next_crawl_at=self.fixed_now + timedelta(days=1),
        )
        waiting_domain = discovery_service._ensure_domain(
            self.db,
            tenant_id="TENANT-1",
            connector_id=waiting.id,
            seed=waiting_seed,
            domain=domain,
            source="seed",
            found_from_url=waiting_seed.seed_url,
            found_context=waiting_seed.name,
            default_approval="approved",
        )
        waiting_frontier = discovery_service._enqueue_frontier_url(
            self.db,
            tenant_id="TENANT-1",
            connector_id=waiting.id,
            seed=waiting_seed,
            domain_row=waiting_domain,
            url="https://status.example/waiting-child",
            parent_url=waiting_seed.seed_url,
            anchor_text="Child",
            context="Waiting",
            depth=1,
            priority=80,
        )
        assert waiting_frontier is not None
        waiting_frontier.next_fetch_at = self.fixed_now + timedelta(seconds=60)
        self.db.commit()
        waiting_engine = discovery_service.IndependentWebDiscoveryEngine(self.db, waiting, None)
        _, waiting_metrics = waiting_engine.run()
        self.assertEqual(waiting_metrics["status"], "frontier_waiting")

        no_due = create_status_connector(
            "Status No Due",
            maximum_domains_per_run=1,
            maximum_pages_per_domain=5,
            maximum_total_pages_per_run=5,
            maximum_run_duration_seconds=60,
        )
        self._create_seed(
            no_due,
            name="No Due Seed",
            seed_url="https://status.example/no-due",
            next_crawl_at=self.fixed_now + timedelta(days=1),
        )
        no_due_engine = discovery_service.IndependentWebDiscoveryEngine(self.db, no_due, None)
        _, no_due_metrics = no_due_engine.run()
        self.assertEqual(no_due_metrics["status"], "no_due_work")


if __name__ == "__main__":
    unittest.main()
