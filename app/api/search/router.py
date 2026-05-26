from fastapi import APIRouter, Request

from app.api.auth.dependencies import CurrentUser
from app.api.search.schemas import SearchQuery, SearchResponse
from app.api.search.service import SearchService
from app.config.database import DBSession
from app.core.rate_limit import limiter

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search(
    request: Request,
    q: str,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = 20,
) -> SearchResponse:
    query = SearchQuery(q=q, limit=limit)
    hits = await SearchService(db).search(
        query=query.q,
        resource_types=query.resource_types,
        limit=query.limit,
        user_id=current_user.id,
    )
    return SearchResponse(query=query.q, hits=hits, total=len(hits))
