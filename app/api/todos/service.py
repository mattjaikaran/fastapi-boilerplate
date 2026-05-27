import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.todos.model import Todo, TodoPriority
from app.api.todos.schemas import (
    TodoBulkDelete,
    TodoBulkUpdate,
    TodoCreate,
    TodoStatsResponse,
    TodoUpdate,
)
from app.core.exceptions import ForbiddenError, NotFoundError


class TodoService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, todo_id: uuid.UUID, user_id: uuid.UUID) -> Todo:
        result = await self.db.get(Todo, todo_id)
        if not result:
            raise NotFoundError(detail=f"Todo {todo_id} not found")
        if result.user_id != user_id:
            raise ForbiddenError()
        return result

    async def list_todos(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        completed: bool | None = None,
        priority: TodoPriority | None = None,
        search: str | None = None,
        overdue: bool | None = None,
        due_today: bool | None = None,
    ) -> tuple[list[Todo], int]:
        query = select(Todo).where(Todo.user_id == user_id)

        if completed is not None:
            query = query.where(Todo.is_completed == completed)
        if priority:
            query = query.where(Todo.priority == priority)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern))
            )

        now = datetime.now(UTC)
        if overdue is True:
            query = query.where(
                Todo.due_at < now,
                Todo.is_completed.is_(False),
            )
        if due_today is True:
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            query = query.where(
                Todo.due_at >= start_of_day,
                Todo.due_at < end_of_day,
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = (
            query.order_by(Todo.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        todos = list((await self.db.execute(query)).scalars().all())

        return todos, total

    async def create(self, user_id: uuid.UUID, data: TodoCreate) -> Todo:
        todo = Todo(user_id=user_id, **data.model_dump())
        self.db.add(todo)
        await self.db.flush()
        await self.db.refresh(todo)
        return todo

    async def update(self, todo: Todo, data: TodoUpdate) -> Todo:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(todo, field, value)
        self.db.add(todo)
        await self.db.flush()
        await self.db.refresh(todo)
        return todo

    async def delete(self, todo: Todo) -> None:
        await self.db.delete(todo)
        await self.db.flush()

    async def toggle(self, todo: Todo) -> Todo:
        todo.is_completed = not todo.is_completed
        self.db.add(todo)
        await self.db.flush()
        await self.db.refresh(todo)
        return todo

    async def bulk_update(self, user_id: uuid.UUID, data: TodoBulkUpdate) -> list[Todo]:
        result = await self.db.execute(
            select(Todo).where(
                Todo.user_id == user_id,
                Todo.id.in_(data.ids),
            )
        )
        todos = list(result.scalars().all())

        for todo in todos:
            if data.is_completed is not None:
                todo.is_completed = data.is_completed
            if data.priority is not None:
                todo.priority = data.priority
            self.db.add(todo)

        await self.db.flush()
        for todo in todos:
            await self.db.refresh(todo)

        return todos

    async def bulk_delete(self, user_id: uuid.UUID, data: TodoBulkDelete) -> int:
        result = await self.db.execute(
            select(Todo).where(
                Todo.user_id == user_id,
                Todo.id.in_(data.ids),
            )
        )
        todos = list(result.scalars().all())
        for todo in todos:
            await self.db.delete(todo)
        await self.db.flush()
        return len(todos)

    async def get_stats(self, user_id: uuid.UUID) -> TodoStatsResponse:
        now = datetime.now(UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        base = select(func.count()).where(Todo.user_id == user_id)

        total = (await self.db.execute(base)).scalar_one()
        completed = (
            await self.db.execute(base.where(Todo.is_completed.is_(True)))
        ).scalar_one()
        pending = (
            await self.db.execute(base.where(Todo.is_completed.is_(False)))
        ).scalar_one()
        overdue = (
            await self.db.execute(
                base.where(Todo.due_at < now, Todo.is_completed.is_(False))
            )
        ).scalar_one()
        due_today = (
            await self.db.execute(
                base.where(Todo.due_at >= start_of_day, Todo.due_at < end_of_day)
            )
        ).scalar_one()

        by_priority: dict[str, int] = {}
        for priority in TodoPriority:
            count = (
                await self.db.execute(base.where(Todo.priority == priority))
            ).scalar_one()
            by_priority[priority.value] = count

        return TodoStatsResponse(
            total=total,
            completed=completed,
            pending=pending,
            overdue=overdue,
            due_today=due_today,
            by_priority=by_priority,
        )
