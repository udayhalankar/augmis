from pydantic import BaseModel


class PlatformConfigUpdateRequest(BaseModel):
    openai_api_key: str | None = None
    openai_model: str | None = None
    openai_embedding_model: str | None = None
    database_url: str | None = None
    ocr_tesseract_cmd: str | None = None


class FrontendLogCreateRequest(BaseModel):
    message: str
    level: str = "ERROR"
    category: str = "client_error"
    route: str | None = None
    method: str | None = None
    status_code: int | None = None
    request_id: str | None = None
    stack: str | None = None
    user_agent: str | None = None
    repository_id: str | None = None
    business_area: str | None = None
    component: str | None = None
    is_critical: bool = False
    metadata: dict | None = None
