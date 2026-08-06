from app.core.connector_exceptions import ConnectorConfigurationError


REQUIRED_CONFIG = {
    "sharedrive": ["root_path"],
    "sharepoint": [
        "tenant_id",
        "client_id",
        "client_secret",
        "site_id",
        "drive_id",
    ],
    "otcs": ["base_url", "folder_id"],
}


def validate_repository_connector_config(repository):
    source_type = repository.source_type
    config = repository.connection_config or {}

    if source_type == "sharepoint":
        required = ["tenant_id", "client_id", "site_id", "drive_id"]
        missing = [field for field in required if not config.get(field)]

        if missing:
            raise ConnectorConfigurationError(
                f"Missing connector configuration fields: {', '.join(missing)}"
            )

        uses_certificate = (config.get("auth_method") or "").lower() == "certificate" or bool(
            config.get("certificate_thumbprint")
            or config.get("certificate_private_key")
            or config.get("certificate_private_key_env")
            or config.get("certificate_private_key_path")
        )

        if uses_certificate:
            if not config.get("certificate_thumbprint"):
                raise ConnectorConfigurationError(
                    "Missing connector configuration fields: certificate_thumbprint"
                )

            if not (
                config.get("certificate_private_key")
                or config.get("certificate_private_key_env")
                or config.get("certificate_private_key_path")
            ):
                raise ConnectorConfigurationError(
                    "Missing connector configuration fields: certificate_private_key or certificate_private_key_env or certificate_private_key_path"
                )

            return True

        if not (config.get("client_secret") or config.get("client_secret_env")):
            raise ConnectorConfigurationError(
                "Missing connector configuration fields: client_secret or client_secret_env"
            )

        return True

    required = REQUIRED_CONFIG.get(source_type, [])
    missing = [field for field in required if not config.get(field)]

    if missing:
        raise ConnectorConfigurationError(
            f"Missing connector configuration fields: {', '.join(missing)}"
        )

    return True


def validate_source_file_contract(source_file: dict):
    required = [
        "external_file_id",
        "file_name",
        "file_path",
    ]

    missing = [key for key in required if not source_file.get(key)]

    if missing:
        raise ConnectorConfigurationError(
            f"Connector file contract missing fields: {', '.join(missing)}"
        )

    return True
