from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel


class RepositoryCreateRequest(BaseModel):
    repository_name: str
    source_type: str
    business_area: Optional[str] = None
    status: str = "ACTIVE"
    source_path: Optional[str] = None
    connection_config: dict[str, Any] = {}


class RepositoryAccessCreateRequest(BaseModel):
    repository_id: str
    user_id: str
    can_read: bool = True
    can_ingest: bool = False
    can_admin: bool = False
    business_area: Optional[str] = None


class RepositoryAccessUpdateRequest(BaseModel):
    can_read: bool = True
    can_ingest: bool = False
    can_admin: bool = False
    business_area: Optional[str] = None


class RepositoryConnectionUpdateRequest(BaseModel):
    source_path: Optional[str] = None
    business_area: Optional[str] = None
    connection_config: dict[str, Any] = {}


class WorkAreaCreateRequest(BaseModel):
    name: str
    description: str = ""
    intelligence_pattern: str = ""
    tags_keywords: list[str] = []
    summary_focus: list[str] = []
    risk_rules: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    required_specifics: list[str] = []
    entities_to_extract: list[str] = []
    summary_template: str = ""
    threshold_rules: list[dict[str, Any]] = []
    fact_extractors: list[dict[str, Any]] = []
    dashboard_type: str = "generic"
    enabled_checks: list[str] = []


class WorkAreaUpdateRequest(BaseModel):
    name: str
    description: str = ""
    intelligence_pattern: str = ""
    tags_keywords: list[str] = []
    summary_focus: list[str] = []
    risk_rules: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    required_specifics: list[str] = []
    entities_to_extract: list[str] = []
    summary_template: str = ""
    threshold_rules: list[dict[str, Any]] = []
    fact_extractors: list[dict[str, Any]] = []
    dashboard_type: str = "generic"
    enabled_checks: list[str] = []


class IntelligencePatternCreateRequest(BaseModel):
    name: str
    description: str = ""
    dashboard_type: str = "generic"
    tags_keywords: list[str] = []
    summary_focus: list[str] = []
    risk_rules: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    required_specifics: list[str] = []
    entities_to_extract: list[str] = []
    summary_template: str = ""
    threshold_rules: list[dict[str, Any]] = []
    fact_extractors: list[dict[str, Any]] = []
    enabled_checks: list[str] = []


class IntelligencePatternUpdateRequest(BaseModel):
    name: str
    description: str = ""
    dashboard_type: str = "generic"
    tags_keywords: list[str] = []
    summary_focus: list[str] = []
    risk_rules: list[dict[str, Any]] = []
    thresholds: list[dict[str, Any]] = []
    required_specifics: list[str] = []
    entities_to_extract: list[str] = []
    summary_template: str = ""
    threshold_rules: list[dict[str, Any]] = []
    fact_extractors: list[dict[str, Any]] = []
    enabled_checks: list[str] = []


def new_repository_id():
    return f"REPO-{str(uuid4())[:8].upper()}"


def new_access_id():
    return f"ACC-{str(uuid4())[:8].upper()}"


def now_iso():
    return datetime.utcnow().isoformat()
