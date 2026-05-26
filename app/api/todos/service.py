import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.todos.model import Todo, TodoPriority
from app.api.todos.schemas import TodoCreate, TodoUpdate
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
    ) -> tuple[list[Todo], int]:
        query = select(Todo).where(Todo.user_id == user_id)

        if completed is not None:
            query = query.where(Todo.is_completed == completed)
        if priority:
            query = query.where(Todo.priority == priority)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.order_by(Todo.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
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
