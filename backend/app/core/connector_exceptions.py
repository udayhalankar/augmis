class ConnectorError(Exception):
    pass


class ConnectorConfigurationError(ConnectorError):
    pass


class ConnectorDiscoveryError(ConnectorError):
    pass


class ConnectorDownloadError(ConnectorError):
    pass


class ConnectorIngestionError(ConnectorError):
    pass


class ConnectorParseError(ConnectorIngestionError):
    pass


class ConnectorChunkingError(ConnectorIngestionError):
    pass


class ConnectorEmbeddingError(ConnectorIngestionError):
    pass


class ConnectorValidationError(ConnectorError):
    pass
