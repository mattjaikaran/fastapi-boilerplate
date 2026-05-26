from pydantic import BaseModel, field_validator


class SearchQuery(BaseModel):
    q: str
    resource_types: list[str] = ["users", "organizations", "todos"]
    limit: int = 20

    @field_validator("q")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Query must be at least 2 characters")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, v: int) -> int:
        return min(max(v, 1), 100)


class SearchHit(BaseModel):
    resource_type: str
    id: str
    title: str
    subtitle: str | None
    rank: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]
    total: int
