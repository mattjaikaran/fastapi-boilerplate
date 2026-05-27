"""Abstract CRUD service base class.

Usage:
    class TodoService(CRUDService["Todo", TodoCreate, TodoUpdate]):
        model = Todo

        async def custom_query(self) -> list[Todo]:
            ...
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError

ModelT = TypeVar("ModelT")
CreateSchemaT = TypeVar("CreateSchemaT")
UpdateSchemaT = TypeVar("UpdateSchemaT")


class CRUDService(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):  # noqa: UP046
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, obj_id: uuid.UUID, **filters: object) -> ModelT:
        obj = await self.db.get(self.model, obj_id)
        if not obj:
            raise NotFoundError(detail=f"{self.model.__name__} {obj_id} not found")
        for attr, value in filters.items():
            if getattr(obj, attr, None) != value:
                raise NotFoundError(detail=f"{self.model.__name__} {obj_id} not found")
        return obj

    async def get_by_field(self, field: str, value: object) -> ModelT | None:
        result = await self.db.execute(
            select(self.model).where(getattr(self.model, field) == value)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        *,
        order_by: str = "created_at",
        desc: bool = True,
        **filters: object,
    ) -> tuple[list[ModelT], int]:
        query = select(self.model)
        for attr, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, attr) == value)

        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        col = getattr(self.model, order_by)
        query = query.order_by(col.desc() if desc else col.asc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        items = list((await self.db.execute(query)).scalars().all())

        return items, total

    async def create(self, data: CreateSchemaT, **extra: object) -> ModelT:
        payload: dict[str, Any] = (
            data.model_dump()  # type: ignore[union-attr]
            if hasattr(data, "model_dump")
            else dict(data)  # type: ignore[call-overload]
        )
        payload.update(extra)
        obj = self.model(**payload)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelT, data: UpdateSchemaT, **extra: object) -> ModelT:
        payload: dict[str, Any] = (
            data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            if hasattr(data, "model_dump")
            else {k: v for k, v in dict(data).items() if v is not None}  # type: ignore[call-overload]
        )
        payload.update(extra)
        for field, value in payload.items():
            setattr(obj, field, value)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)
        await self.db.flush()

    async def soft_delete(self, obj: ModelT) -> None:
        from datetime import UTC, datetime

        if not hasattr(obj, "deleted_at"):
            msg = f"{self.model.__name__} does not support soft delete"
            raise NotImplementedError(msg)
        obj.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
        self.db.add(obj)
        await self.db.flush()

    async def count(self, **filters: object) -> int:
        query = select(func.count()).select_from(self.model)  # type: ignore[arg-type]
        for attr, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, attr) == value)
        return (await self.db.execute(query)).scalar_one()

    async def exists(self, **filters: object) -> bool:
        return (await self.count(**filters)) > 0
