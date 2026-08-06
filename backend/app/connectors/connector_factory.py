from app.connectors.otcs_connector import OTCSConnector
from app.connectors.sharepoint_connector import SharePointGraphConnector
from app.connectors.sharedrive_connector import SharedDriveConnector


def get_connector(repository: dict):
    source_type = repository.get("source_type")

    if source_type == "sharedrive":
        return SharedDriveConnector(repository)

    if source_type == "sharepoint":
        return SharePointGraphConnector(repository)

    if source_type == "otcs":
        return OTCSConnector(repository)

    raise ValueError(f"Unsupported connector type: {source_type}")
