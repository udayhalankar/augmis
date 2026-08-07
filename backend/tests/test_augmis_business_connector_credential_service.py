from __future__ import annotations

import base64
import unittest
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import augmis_business as augmis_business_routes
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.db_models import (
    AuditLog,
    BusinessDevelopmentConnector,
    BusinessDevelopmentConnectorSecret,
    Tenant,
    User,
)
from app.services.augmis_business_connector_credential_service import (
    delete_connector_credential,
    get_connector_credential_status,
    resolve_provider_credential,
    save_connector_credential,
    test_connector_credential,
)
from app.services.augmis_business_web_search_provider import WebSearchProviderError


def _valid_secret_key(seed: bytes) -> str:
    return base64.urlsafe_b64encode(seed).decode("utf-8").rstrip("=")


class AugmisBusinessConnectorCredentialServiceTest(unittest.TestCase):
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
                BusinessDevelopmentConnector.__table__,
                BusinessDevelopmentConnectorSecret.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": [
                "business_development:read",
                "business_development:admin",
            ],
            "allowed_modules": ["augmis_business"],
        }
        self.read_only_user = {
            **self.current_user,
            "permissions": ["business_development:read"],
        }
        self.original_secret_key = settings.AUGMIS_CONNECTOR_SECRET_KEY
        self.original_tavily_key = settings.TAVILY_API_KEY
        self.original_brave_key = settings.BRAVE_SEARCH_API_KEY
        settings.AUGMIS_CONNECTOR_SECRET_KEY = _valid_secret_key(b"1" * 32)
        settings.TAVILY_API_KEY = None
        settings.BRAVE_SEARCH_API_KEY = None
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
                User(
                    user_id="USER-2",
                    tenant_id="TENANT-2",
                    name="Read Only",
                    email="bd.reader@example.com",
                    password_hash="x",
                    role="user",
                    status="ACTIVE",
                ),
            ]
        )
        self.db.commit()

    def tearDown(self):
        settings.AUGMIS_CONNECTOR_SECRET_KEY = self.original_secret_key
        settings.TAVILY_API_KEY = self.original_tavily_key
        settings.BRAVE_SEARCH_API_KEY = self.original_brave_key
        self.db.close()

    def _build_client(self, user: dict) -> TestClient:
        app = FastAPI()
        app.include_router(augmis_business_routes.router)

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    def test_save_encrypts_value_and_response_remains_write_only(self):
        result = save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-secret-1234",
        )
        row = (
            self.db.query(BusinessDevelopmentConnectorSecret)
            .filter(BusinessDevelopmentConnectorSecret.tenant_id == "TENANT-1")
            .one()
        )
        self.assertNotEqual(row.encrypted_value, "tvly-secret-1234")
        self.assertEqual(row.provider, "tavily")
        self.assertTrue(result["data"]["configured"])
        self.assertEqual(result["data"]["credential_source"], "tenant_secret")
        self.assertEqual(result["data"]["masked_hint"], "Ends in 1234")
        self.assertNotIn("api_key", result["data"])
        self.assertNotIn("encrypted_value", result["data"])

    def test_tenant_secret_overrides_environment(self):
        settings.TAVILY_API_KEY = "tvly-env-9999"
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        resolved = resolve_provider_credential(self.db, "TENANT-1", "tavily")
        self.assertEqual(resolved.api_key, "tvly-tenant-1234")
        self.assertEqual(resolved.credential_source, "tenant_secret")

    def test_environment_fallback_is_used_and_restored_after_clear(self):
        settings.TAVILY_API_KEY = "tvly-env-5678"
        initial = get_connector_credential_status(self.db, "TENANT-1", "tavily")
        self.assertEqual(initial["data"]["credential_source"], "environment")
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        cleared = delete_connector_credential(self.db, "TENANT-1", "tavily", self.current_user)
        resolved = resolve_provider_credential(self.db, "TENANT-1", "tavily")
        self.assertEqual(cleared["deleted"], 1)
        self.assertEqual(cleared["data"]["credential_source"], "environment")
        self.assertEqual(resolved.api_key, "tvly-env-5678")
        self.assertEqual(resolved.credential_source, "environment")

    def test_missing_both_returns_unconfigured_status(self):
        status_result = get_connector_credential_status(self.db, "TENANT-1", "tavily")
        test_result = test_connector_credential(self.db, "TENANT-1", "tavily", self.current_user)
        self.assertFalse(status_result["data"]["configured"])
        self.assertEqual(status_result["data"]["credential_source"], "none")
        self.assertFalse(test_result["data"]["result"]["success"])
        self.assertEqual(test_result["data"]["result"]["message"], "Tavily API key is not configured.")

    def test_provider_resolution_has_no_cross_provider_fallback(self):
        settings.BRAVE_SEARCH_API_KEY = "brave-env-2222"
        tavily = resolve_provider_credential(self.db, "TENANT-1", "tavily")
        brave = resolve_provider_credential(self.db, "TENANT-1", "brave")
        self.assertIsNone(tavily.api_key)
        self.assertEqual(tavily.credential_source, "none")
        self.assertEqual(brave.api_key, "brave-env-2222")
        self.assertEqual(brave.credential_source, "environment")

    def test_wrong_master_key_fails_safely(self):
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        settings.AUGMIS_CONNECTOR_SECRET_KEY = _valid_secret_key(b"2" * 32)
        with self.assertRaisesRegex(Exception, "Stored provider credential could not be decrypted."):
            resolve_provider_credential(self.db, "TENANT-1", "tavily")

    def test_malformed_ciphertext_fails_safely(self):
        self.db.add(
            BusinessDevelopmentConnectorSecret(
                id="BD-SEC-BAD-CIPHER",
                tenant_id="TENANT-1",
                connector_id=None,
                provider="tavily",
                credential_type="api_key",
                encrypted_value="not-base64",
                key_version="v1",
                status="active",
                created_by="USER-1",
                updated_by="USER-1",
            )
        )
        self.db.commit()
        with self.assertRaisesRegex(Exception, "Stored provider credential could not be decrypted."):
            resolve_provider_credential(self.db, "TENANT-1", "tavily")

    def test_tenant_isolation_hides_other_tenant_secret(self):
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        other_status = get_connector_credential_status(self.db, "TENANT-2", "tavily")
        delete_result = delete_connector_credential(
            self.db,
            "TENANT-2",
            "tavily",
            {
                **self.current_user,
                "tenant_id": "TENANT-2",
                "user_id": "USER-2",
            },
        )
        self.assertFalse(other_status["data"]["configured"])
        self.assertEqual(delete_result["deleted"], 0)

    def test_read_only_user_cannot_mutate_credential_routes(self):
        client = self._build_client(self.read_only_user)
        post_response = client.post(
            "/api/augmis-business/connector-credentials/tavily",
            json={"api_key": "tvly-tenant-1234"},
        )
        delete_response = client.delete("/api/augmis-business/connector-credentials/tavily")
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    @patch("app.services.augmis_business_connector_credential_service.get_web_search_provider")
    def test_stored_credential_is_used_for_provider_test(self, mock_get_provider: Mock):
        mock_provider = Mock()
        mock_provider.test_connection.return_value = {
            "success": True,
            "message": "Tavily API key is configured and the provider returned results.",
            "provider": "tavily",
            "result_count": 1,
        }
        mock_get_provider.return_value = mock_provider
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        result = test_connector_credential(self.db, "TENANT-1", "tavily", self.current_user)
        self.assertTrue(result["data"]["result"]["success"])
        mock_get_provider.assert_called_once_with("tavily", api_key="tvly-tenant-1234")

    @patch("app.services.augmis_business_connector_credential_service.get_web_search_provider")
    def test_provider_test_failure_is_safe_and_does_not_echo_key(self, mock_get_provider: Mock):
        mock_provider = Mock()
        mock_provider.test_connection.side_effect = WebSearchProviderError("Tavily rejected the API key.")
        mock_get_provider.return_value = mock_provider
        save_connector_credential(
            self.db,
            "TENANT-1",
            "tavily",
            self.current_user,
            "tvly-tenant-1234",
        )
        result = test_connector_credential(self.db, "TENANT-1", "tavily", self.current_user)
        self.assertFalse(result["data"]["result"]["success"])
        self.assertEqual(result["data"]["last_test_status"], "failed")
        self.assertNotIn("tvly-tenant-1234", result["data"]["result"]["message"])


if __name__ == "__main__":
    unittest.main()
