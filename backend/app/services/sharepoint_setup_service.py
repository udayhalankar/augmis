from urllib.parse import quote

from app.connectors.sharepoint_connector import SharePointGraphConnector


def discover_sites(config: dict, search: str = ""):
    connector = SharePointGraphConnector(
        {"connection_config": config},
        require_resource_targets=False,
    )

    if search:
        url = f"https://graph.microsoft.com/v1.0/sites?search={quote(search)}"
    else:
        url = "https://graph.microsoft.com/v1.0/sites?search=*"

    data = connector._graph_get_json(url)

    return [
        {
            "id": site.get("id"),
            "name": site.get("name"),
            "display_name": site.get("displayName"),
            "web_url": site.get("webUrl"),
        }
        for site in data.get("value", [])
    ]


def discover_drives(config: dict):
    connector = SharePointGraphConnector(
        {"connection_config": config},
        require_resource_targets=False,
    )
    site_id = config.get("site_id")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    data = connector._graph_get_json(url)

    return [
        {
            "id": drive.get("id"),
            "name": drive.get("name"),
            "drive_type": drive.get("driveType"),
            "web_url": drive.get("webUrl"),
        }
        for drive in data.get("value", [])
    ]


def discover_drive_folders(config: dict, folder_path: str = "/"):
    connector = SharePointGraphConnector(
        {"connection_config": config},
        require_resource_targets=False,
    )
    drive_id = config.get("drive_id")

    if folder_path in ["/", "", None]:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"
    else:
        clean_path = folder_path.strip("/")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{clean_path}:/children"

    data = connector._graph_get_json(url)

    return [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "path": f"{folder_path.rstrip('/')}/{item.get('name')}".replace("//", "/"),
            "web_url": item.get("webUrl"),
            "is_folder": bool(item.get("folder")),
            "is_file": bool(item.get("file")),
        }
        for item in data.get("value", [])
    ]
