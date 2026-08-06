from datetime import datetime
import os
from urllib.parse import quote

import requests

try:
    import msal
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    msal = None

from app.connectors.base_connector import BaseConnector
from app.core.connector_exceptions import (
    ConnectorConfigurationError,
    ConnectorDiscoveryError,
    ConnectorDownloadError,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class SharePointGraphConnector(BaseConnector):
    def __init__(self, repository: dict, require_resource_targets: bool = True):
        super().__init__(repository)

        self.azure_tenant_id = self.config.get("tenant_id")
        self.client_id = self.config.get("client_id")
        self.auth_method = (self.config.get("auth_method") or "client_secret").lower()
        self.client_secret = self.config.get("client_secret")
        self.client_secret_env = self.config.get("client_secret_env")
        self.certificate_thumbprint = self.config.get("certificate_thumbprint")
        self.certificate_private_key = self.config.get("certificate_private_key")
        self.certificate_private_key_env = self.config.get("certificate_private_key_env")
        self.certificate_private_key_path = self.config.get("certificate_private_key_path")
        self.certificate_passphrase = self.config.get("certificate_passphrase")
        self.certificate_passphrase_env = self.config.get("certificate_passphrase_env")
        self.site_id = self.config.get("site_id")
        self.drive_id = self.config.get("drive_id")
        self.folder_path = self.config.get("folder_path") or "/"
        self.delta_link = self.config.get("delta_link")
        self.require_resource_targets = require_resource_targets
        self._access_token = None

        self._validate_config()

    def _validate_config(self):
        required = ["tenant_id", "client_id"]
        if self.require_resource_targets:
            required.extend(["site_id", "drive_id"])
        missing = [key for key in required if not self.config.get(key)]

        if missing:
            raise ConnectorConfigurationError(
                f"SharePoint connector missing fields: {', '.join(missing)}"
            )

        if self._use_certificate_auth():
            if not self.certificate_thumbprint:
                raise ConnectorConfigurationError(
                    "SharePoint certificate auth requires certificate_thumbprint"
                )

            if not (
                self.certificate_private_key
                or self.certificate_private_key_env
                or self.certificate_private_key_path
            ):
                raise ConnectorConfigurationError(
                    "SharePoint certificate auth requires a private key value, env reference, or file path"
                )
            return

        if not (self.client_secret or self.client_secret_env):
            raise ConnectorConfigurationError(
                "SharePoint client secret auth requires client_secret or client_secret_env"
            )

    def _use_certificate_auth(self) -> bool:
        return self.auth_method == "certificate" or bool(
            self.certificate_thumbprint
            or self.certificate_private_key
            or self.certificate_private_key_env
            or self.certificate_private_key_path
        )

    def _resolve_env_value(self, env_key: str | None, label: str) -> str | None:
        if not env_key:
            return None

        value = os.getenv(env_key)
        if not value:
            raise ConnectorConfigurationError(
                f"SharePoint {label} env var '{env_key}' is not set"
            )

        return value

    def _resolve_private_key(self) -> str:
        if self.certificate_private_key:
            return self.certificate_private_key

        env_value = self._resolve_env_value(
            self.certificate_private_key_env,
            "certificate private key",
        )
        if env_value:
            return env_value

        if self.certificate_private_key_path:
            try:
                with open(self.certificate_private_key_path, "r", encoding="utf-8") as handle:
                    return handle.read()
            except OSError as exc:
                raise ConnectorConfigurationError(
                    f"Unable to read SharePoint certificate private key file: {exc}"
                ) from exc

        raise ConnectorConfigurationError("SharePoint certificate private key is missing")

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        if msal is None:
            raise ConnectorConfigurationError(
                "MSAL is not installed. Install backend requirements to enable SharePoint sync."
            )

        authority = f"https://login.microsoftonline.com/{self.azure_tenant_id}"
        client_credential = None

        if self._use_certificate_auth():
            client_credential = {
                "private_key": self._resolve_private_key(),
                "thumbprint": self.certificate_thumbprint,
            }

            passphrase = self.certificate_passphrase or self._resolve_env_value(
                self.certificate_passphrase_env,
                "certificate passphrase",
            )
            if passphrase:
                client_credential["passphrase"] = passphrase
        else:
            client_credential = self.client_secret or self._resolve_env_value(
                self.client_secret_env,
                "client secret",
            )

        app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=client_credential,
            authority=authority,
        )

        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" not in result:
            raise ConnectorConfigurationError(
                result.get("error_description") or "Unable to acquire Graph access token"
            )

        self._access_token = result["access_token"]
        return self._access_token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
        }

    def _graph_get_json(self, url: str):
        try:
            response = requests.get(url, headers=self._headers(), timeout=90)

            if response.status_code >= 400:
                raise ConnectorDiscoveryError(
                    f"Graph GET failed {response.status_code}: {response.text}"
                )

            return response.json()
        except requests.RequestException as exc:
            raise ConnectorDiscoveryError(str(exc)) from exc

    def _graph_get_bytes(self, url: str):
        try:
            response = requests.get(url, headers=self._headers(), timeout=180)

            if response.status_code >= 400:
                raise ConnectorDownloadError(
                    f"Graph download failed {response.status_code}: {response.text}"
                )

            return response.content
        except requests.RequestException as exc:
            raise ConnectorDownloadError(str(exc)) from exc

    def _parse_datetime(self, value):
        if not value:
            return None

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    def _folder_item_url(self):
        if self.folder_path in ["/", "", None]:
            return f"{GRAPH_BASE_URL}/drives/{self.drive_id}/root"

        clean_path = self.folder_path.strip("/")
        encoded_path = quote(clean_path)
        return f"{GRAPH_BASE_URL}/drives/{self.drive_id}/root:/{encoded_path}"

    def _delta_start_url(self):
        if self.folder_path in ["/", "", None]:
            return f"{GRAPH_BASE_URL}/drives/{self.drive_id}/root/delta"

        folder_item = self._graph_get_json(self._folder_item_url())
        folder_id = folder_item.get("id")

        if not folder_id:
            raise ConnectorDiscoveryError("Unable to resolve SharePoint delta folder item")

        return f"{GRAPH_BASE_URL}/drives/{self.drive_id}/items/{folder_id}/delta"

    def _download_url(self, item_id: str):
        return f"{GRAPH_BASE_URL}/drives/{self.drive_id}/items/{item_id}/content"

    def _normalize_drive_item(self, item: dict):
        item_id = item.get("id")
        item_name = item.get("name")

        parent_ref = item.get("parentReference", {}) or {}
        parent_path = parent_ref.get("path") or ""
        path_marker = f"/drives/{self.drive_id}/root:"
        relative_parent_path = ""

        if path_marker in parent_path:
            relative_parent_path = parent_path.split(path_marker, 1)[-1].strip("/")

        item_path = (
            f"{relative_parent_path}/{item_name}".strip("/") if item_name else item_id
        )

        hashes = item.get("file", {}).get("hashes", {}) or {}
        file_hash = (
            hashes.get("sha256Hash")
            or hashes.get("quickXorHash")
            or item.get("eTag")
            or item.get("cTag")
        )

        is_deleted = bool(item.get("deleted"))

        return {
            "external_file_id": item_id,
            "file_name": item_name or item_id,
            "file_path": item_path,
            "file_hash": file_hash,
            "file_size": item.get("size"),
            "created_at": self._parse_datetime(item.get("createdDateTime")),
            "modified_at": self._parse_datetime(item.get("lastModifiedDateTime")),
            "is_deleted": is_deleted,
            "metadata": {
                "sharepoint_item_id": item_id,
                "sharepoint_drive_id": self.drive_id,
                "sharepoint_site_id": self.site_id,
                "web_url": item.get("webUrl"),
                "etag": item.get("eTag"),
                "ctag": item.get("cTag"),
                "mime_type": item.get("file", {}).get("mimeType"),
                "deleted": item.get("deleted"),
                "raw_parent_path": parent_path,
            },
        }

    def test_connection(self):
        url = f"{GRAPH_BASE_URL}/sites/{self.site_id}/drives/{self.drive_id}"
        data = self._graph_get_json(url)

        return {
            "ok": True,
            "drive_id": data.get("id"),
            "drive_name": data.get("name"),
            "drive_type": data.get("driveType"),
            "web_url": data.get("webUrl"),
        }

    def list_files(self):
        return self.list_files_delta()["files"]

    def list_files_delta(self, delta_link: str | None = None):
        next_url = delta_link or self.delta_link or self._delta_start_url()
        files = []
        latest_delta_link = None

        while next_url:
            data = self._graph_get_json(next_url)

            for item in data.get("value", []):
                item_id = item.get("id")

                if not item_id:
                    continue

                if item.get("folder") and not item.get("deleted"):
                    continue

                if not item.get("file") and not item.get("deleted"):
                    continue

                files.append(self._normalize_drive_item(item))

            next_url = data.get("@odata.nextLink")
            latest_delta_link = data.get("@odata.deltaLink") or latest_delta_link

        deduped = {}
        for item in files:
            deduped[item["external_file_id"]] = item

        files = list(deduped.values())

        return {
            "files": files,
            "delta_link": latest_delta_link,
            "is_delta": bool(delta_link or self.delta_link),
        }

    def get_file_content(self, source_file: dict) -> bytes:
        if source_file.get("is_deleted"):
            raise ConnectorDownloadError("Cannot download deleted SharePoint item")

        item_id = source_file.get("external_file_id")

        if not item_id:
            raise ConnectorDownloadError("Missing SharePoint item id")

        return self._graph_get_bytes(self._download_url(item_id))
