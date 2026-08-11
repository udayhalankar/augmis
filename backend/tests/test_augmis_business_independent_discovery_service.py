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
        listener_service._now = lambda: self.fixed_now
        discovery_service._now = lambda: self.fixed_now
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
        self.db.close()

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
        mock_fetch_page.return_value = {
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
        }

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
        mock_fetch_page.return_value = {
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
        }

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
                      <head><title>Workflow Automation RFP 2026</title></head>
                      <body>
                        <h1>Workflow Automation RFP 2026</h1>
                        <p>Request for proposal for workflow automation and document management system.</p>
                        <p>Reference Number: WF-2026-09</p>
                        <p>Closing Date: 25/08/2026</p>
                      </body>
                    </html>
                """,
                "bytes_read": 260,
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

        self.assertEqual(result["run"]["run_metadata_json"]["listing_pages"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_links_discovered"], 1)
        self.assertEqual(result["run"]["run_metadata_json"]["detail_links_queued"], 1)

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


if __name__ == "__main__":
    unittest.main()
