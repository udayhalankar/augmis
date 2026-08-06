from pydantic import BaseModel


class RepositoryRebuildRequest(BaseModel):
    repository_id: str
