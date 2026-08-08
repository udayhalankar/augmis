from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorSecret,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentSearchProvider,
    BusinessDevelopmentSearchProfile,
    Tenant,
    User,
)
from app.models.augmis_business_models import AugmisBusinessSearchProviderCreateRequest
from app.services import augmis_business_listener_service as listener_service
from app.services import augmis_business_search_provider_service as provider_service


class AugmisBusinessSearchProviderServiceTest(unittest.TestCase):
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
                BusinessDevelopmentSearchProfile.__table__,
                BusinessDevelopmentSearchProvider.__table__,
                BusinessDevelopmentConnector.__table__,
                BusinessDevelopmentConnectorSecret.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": ["business_development:read", "business_development:admin"],
            "allowed_modules": ["augmis_business"],
        }
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
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_builtin_providers_are_seeded_and_listed(self):
        result = provider_service.list_search_providers(self.db, "TENANT-1")
        provider_codes = [item["provider_code"] for item in result["data"]]
        self.assertIn("tavily", provider_codes)
        self.assertIn("brave", provider_codes)

    def test_custom_provider_create_and_duplicate_code_rejected(self):
        payload = AugmisBusinessSearchProviderCreateRequest(
            provider_code="custom-rfp-search",
            display_name="Custom RFP Search",
            provider_type="generic_rest",
            enabled=True,
            credential_type="api_key",
            configuration_json={
                "base_search_url": "https://search.example/api",
                "http_method": "get",
                "authentication_type": "api_key_header",
                "api_key_header_name": "X-API-Key",
                "query_parameter_name": "q",
                "results_path": "results",
                "title_field": "title",
                "url_field": "url",
                "snippet_field": "snippet",
            },
        )
        with patch("app.services.augmis_business_search_provider_service.validate_public_http_url"):
            created = provider_service.create_search_provider(self.db, "TENANT-1", self.current_user, payload)
        self.assertEqual(created["data"]["provider_code"], "custom-rfp-search")
        with self.assertRaisesRegex(Exception, "Provider code already exists."):
            with patch("app.services.augmis_business_search_provider_service.validate_public_http_url"):
                provider_service.create_search_provider(self.db, "TENANT-1", self.current_user, payload)

    def test_http_provider_url_is_rejected(self):
        payload = AugmisBusinessSearchProviderCreateRequest(
            provider_code="http-search",
            display_name="HTTP Search",
            provider_type="generic_rest",
            enabled=True,
            credential_type="api_key",
            configuration_json={
                "base_search_url": "http://search.example/api",
                "http_method": "get",
                "authentication_type": "api_key_header",
                "api_key_header_name": "X-API-Key",
                "query_parameter_name": "q",
                "results_path": "results",
                "title_field": "title",
                "url_field": "url",
                "snippet_field": "snippet",
            },
        )
        with self.assertRaisesRegex(Exception, "Provider endpoint must use HTTPS."):
            provider_service.create_search_provider(self.db, "TENANT-1", self.current_user, payload)

    def test_custom_provider_is_tenant_scoped(self):
        payload = AugmisBusinessSearchProviderCreateRequest(
            provider_code="tenant-a-search",
            display_name="Tenant A Search",
            provider_type="generic_rest",
            enabled=True,
            credential_type="api_key",
            configuration_json={
                "base_search_url": "https://search.example/api",
                "http_method": "get",
                "authentication_type": "api_key_header",
                "api_key_header_name": "X-API-Key",
                "query_parameter_name": "q",
                "results_path": "results",
                "title_field": "title",
                "url_field": "url",
                "snippet_field": "snippet",
            },
        )
        with patch("app.services.augmis_business_search_provider_service.validate_public_http_url"):
            provider_service.create_search_provider(self.db, "TENANT-1", self.current_user, payload)
        with self.assertRaisesRegex(Exception, "Search provider not found."):
            provider_service.resolve_search_provider_by_code(self.db, "TENANT-2", "tenant-a-search")

    def test_disabled_provider_cannot_be_selected(self):
        payload = AugmisBusinessSearchProviderCreateRequest(
            provider_code="disabled-search",
            display_name="Disabled Search",
            provider_type="generic_rest",
            enabled=False,
            credential_type="api_key",
            configuration_json={
                "base_search_url": "https://search.example/api",
                "http_method": "get",
                "authentication_type": "api_key_header",
                "api_key_header_name": "X-API-Key",
                "query_parameter_name": "q",
                "results_path": "results",
                "title_field": "title",
                "url_field": "url",
                "snippet_field": "snippet",
            },
        )
        with patch("app.services.augmis_business_search_provider_service.validate_public_http_url"):
            created = provider_service.create_search_provider(self.db, "TENANT-1", self.current_user, payload)
        connector = listener_service.ensure_web_search_connector(self.db, "TENANT-1", self.current_user)
        with self.assertRaisesRegex(Exception, "Provider is disabled."):
            listener_service.set_connector_provider(
                self.db,
                "TENANT-1",
                connector.id,
                self.current_user,
                created["data"]["provider_code"],
            )


if __name__ == "__main__":
    unittest.main()
