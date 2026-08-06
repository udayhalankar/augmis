from app.connectors.base_connector import BaseConnector


class OTCSConnector(BaseConnector):
    def list_files(self) -> list[dict]:
        return []

    def get_file_content(self, source_file: dict) -> bytes:
        raise NotImplementedError("OTCS connector content download is not implemented yet")
