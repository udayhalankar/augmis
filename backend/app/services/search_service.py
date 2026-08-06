from sqlalchemy.orm import Session

from app.services.pgvector_search_service import search_pgvector


def search_documents(
    query: str,
    current_user: dict,
    db: Session,
    top_k: int = 10,
    business_area: str = "All",
):
    return search_pgvector(
        query=query,
        current_user=current_user,
        db=db,
        top_k=top_k,
        business_area=business_area,
    )
