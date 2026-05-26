import uuid

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ClauseElement

from app.api.search.schemas import SearchHit


class SearchService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query: str,
        resource_types: list[str],
        limit: int,
        user_id: uuid.UUID,
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        tsquery = func.plainto_tsquery("english", query)

        if "users" in resource_types:
            hits.extend(await self._search_users(query, tsquery, limit))
        if "organizations" in resource_types:
            hits.extend(
                await self._search_organizations(query, tsquery, limit, user_id)
            )
        if "todos" in resource_types:
            hits.extend(await self._search_todos(query, tsquery, limit, user_id))

        hits.sort(key=lambda h: h.rank, reverse=True)
        return hits[:limit]

    async def _search_users(
        self, query: str, tsquery: ClauseElement, limit: int
    ) -> list[SearchHit]:
        from app.api.users.model import User

        ilike = f"%{query}%"
        q = (
            select(
                User.id,
                User.email,
                User.first_name,
                User.last_name,
                func.ts_rank(
                    func.to_tsvector(
                        "english",
                        func.concat_ws(
                            " ", User.email, User.first_name, User.last_name
                        ),
                    ),
                    tsquery,
                ).label("rank"),
            )
            .where(
                or_(
                    User.email.ilike(ilike),
                    User.first_name.ilike(ilike),
                    User.last_name.ilike(ilike),
                    func.to_tsvector(
                        "english",
                        func.concat_ws(
                            " ", User.email, User.first_name, User.last_name
                        ),
                    ).op("@@")(tsquery),
                ),
                User.deleted_at.is_(None),
            )
            .order_by(text("rank DESC"))
            .limit(limit)
        )
        rows = (await self.db.execute(q)).all()
        return [
            SearchHit(
                resource_type="users",
                id=str(row.id),
                title=row.email,
                subtitle=f"{row.first_name or ''} {row.last_name or ''}".strip()
                or None,
                rank=float(row.rank or 0.0),
            )
            for row in rows
        ]

    async def _search_organizations(
        self, query: str, tsquery: ClauseElement, limit: int, user_id: uuid.UUID
    ) -> list[SearchHit]:
        from app.api.organizations.model import Organization, OrganizationMember

        ilike = f"%{query}%"
        q = (
            select(
                Organization.id,
                Organization.name,
                Organization.slug,
                func.ts_rank(
                    func.to_tsvector(
                        "english",
                        func.concat_ws(" ", Organization.name, Organization.slug),
                    ),
                    tsquery,
                ).label("rank"),
            )
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(
                OrganizationMember.user_id == user_id,
                or_(
                    Organization.name.ilike(ilike),
                    Organization.slug.ilike(ilike),
                    func.to_tsvector(
                        "english",
                        func.concat_ws(" ", Organization.name, Organization.slug),
                    ).op("@@")(tsquery),
                ),
            )
            .order_by(text("rank DESC"))
            .limit(limit)
        )
        rows = (await self.db.execute(q)).all()
        return [
            SearchHit(
                resource_type="organizations",
                id=str(row.id),
                title=row.name,
                subtitle=row.slug,
                rank=float(row.rank or 0.0),
            )
            for row in rows
        ]

    async def _search_todos(
        self, query: str, tsquery: ClauseElement, limit: int, user_id: uuid.UUID
    ) -> list[SearchHit]:
        from app.api.todos.model import Todo

        ilike = f"%{query}%"
        q = (
            select(
                Todo.id,
                Todo.title,
                func.ts_rank(
                    func.to_tsvector("english", Todo.title),
                    tsquery,
                ).label("rank"),
            )
            .where(
                Todo.user_id == user_id,
                or_(
                    Todo.title.ilike(ilike),
                    func.to_tsvector("english", Todo.title).op("@@")(tsquery),
                ),
                Todo.deleted_at.is_(None),
            )
            .order_by(text("rank DESC"))
            .limit(limit)
        )
        rows = (await self.db.execute(q)).all()
        return [
            SearchHit(
                resource_type="todos",
                id=str(row.id),
                title=row.title,
                subtitle=None,
                rank=float(row.rank or 0.0),
            )
            for row in rows
        ]
