from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_saas_access
from app.services.document_browse_service import browse_indexed_documents
from app.services.search_service import search_documents

router = APIRouter(prefix="/search", tags=["Search"])


class SearchRequest(BaseModel):
    query: str | None = None
    q: str | None = None
    top_k: int = 10
    n_results: int | None = None
    business_area: str | None = None


def _run_search(
    query: str,
    top_k: int,
    business_area: str,
    current_user: dict,
    db: Session,
):
    result = search_documents(
        query=query,
        current_user=current_user,
        db=db,
        top_k=top_k,
        business_area=business_area,
    )
    return {
        "success": result.get("success", True),
        "results": result.get("data", []),
        "message": result.get("message"),
        "status": result.get("status", {}),
    }


@router.get("")
def search_route_get(
    q: str = Query(...),
    top_k: int = 10,
    business_area: str = Query("All"),
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return _run_search(q, top_k, business_area, current_user, db)


@router.get("/browse")
def browse_route_get(
    limit: int = 50,
    repository_id: str | None = None,
    file_name: str | None = None,
    business_area: str | None = None,
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    return browse_indexed_documents(
        current_user=current_user,
        db=db,
        limit=limit,
        repository_id=repository_id,
        file_name=file_name,
        business_area=business_area,
    )


@router.post("")
def search_route_post(
    payload: SearchRequest,
    current_user: dict = Depends(require_saas_access("documents", "documents:read")),
    db: Session = Depends(get_db),
):
    query = (payload.query or payload.q or "").strip()
    top_k = payload.n_results or payload.top_k or 10

    if not query:
        return {
            "success": True,
            "results": [],
            "message": "Search query is required",
            "status": {
                "query": query,
                "search_mode": "none",
                "result_count": 0,
                "allowed_repository_count": None,
                "allowed_business_areas": [],
                "message": "Search query is required",
            },
        }

    return _run_search(query, top_k, payload.business_area or "All", current_user, db)
