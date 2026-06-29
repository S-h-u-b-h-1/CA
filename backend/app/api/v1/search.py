from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User
from app.schemas.schemas import SearchResult
from app.api.deps import get_current_user
from app.services.search import universal_search

router = APIRouter()

@router.get("", response_model=SearchResult)
def search_universe(
    q: str = Query(..., min_length=1, description="Search query string"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        results = universal_search(db, current_user.organization_id, q)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during search processing: {str(e)}"
        )
