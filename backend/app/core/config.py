from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    OPENAI_API_KEY: str
    AUTH_JWT_SECRET: str
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OCR_TESSERACT_CMD: str | None = None
    DATASOURCE_PATH: str | None = None
    CHROMA_PATH: str = "./index_store/chroma"
    COLLECTION_NAME: str = "infomentica_dss_docs"
    DATABASE_URL: str
    VECTOR_BACKEND: str = "pgvector"
    CONNECTOR_SYNC_SCHEDULER_MODE: str = "embedded"
    CONNECTOR_SYNC_SCHEDULER_ENABLED: bool = True
    CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES: int = 5
    CONNECTOR_SYNC_SCHEDULER_TIMEZONE: str = "UTC"
    CHUNK_MAX_CHARS: int = 1400
    CHUNK_OVERLAP_CHARS: int = 150
    CORS_ALLOW_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://augmis.com,https://www.augmis.com"
    AUTH_GOOGLE_LOGIN_ENABLED: bool = False
    AUTH_MFA_ENABLED: bool = False
    AUTH_EMAIL_PROVIDER: str = "demo"
    AUTH_SMTP_HOST: str | None = None
    AUTH_SMTP_PORT: int = 587
    AUTH_SMTP_USERNAME: str | None = None
    AUTH_SMTP_PASSWORD: str | None = None
    AUTH_SMTP_FROM_EMAIL: str = "no-reply@augmis.local"
    AUTH_RESET_LINK_BASE_URL: str
    AUTH_REFRESH_TOKEN_DAYS: int = 14
    AUTH_ACCESS_TOKEN_MINUTES: int = 30
    AUTH_SESSION_IDLE_TIMEOUT_MINUTES: int = 30
    AUTH_SESSION_ABSOLUTE_TIMEOUT_HOURS: int = 12
    AUTH_REMEMBER_ME_SESSION_DAYS: int = 30
    AUGMIS_CONNECTOR_SECRET_KEY: str | None = None
    TAVILY_API_KEY: str | None = None
    TAVILY_SEARCH_BASE_URL: str = "https://api.tavily.com/search"
    BRAVE_SEARCH_API_KEY: str | None = None
    BRAVE_SEARCH_BASE_URL: str = "https://api.search.brave.com/res/v1/web/search"
    AUGMIS_WEB_SEARCH_TIMEOUT_SECONDS: int = 20
    AUGMIS_WEB_FETCH_TIMEOUT_SECONDS: int = 15
    AUGMIS_WEB_FETCH_MAX_BYTES: int = 300000
    AUGMIS_WEB_FETCH_MAX_REDIRECTS: int = 3

settings = Settings()
