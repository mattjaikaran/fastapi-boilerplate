import uuid

from fastapi import APIRouter, Query

from app.api.auth.dependencies import CurrentUser
from app.api.todos.model import TodoPriority
from app.api.todos.schemas import (
    TodoCreate,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
)
from app.api.todos.service import TodoService
from app.config.database import DBSession

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=TodoListResponse)
async def list_todos(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    completed: bool | None = Query(default=None),
    priority: TodoPriority | None = Query(default=None),
) -> TodoListResponse:
    service = TodoService(db)
    todos, total = await service.list_todos(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        completed=completed,
        priority=priority,
    )
    pages = -(-total // page_size)
    return TodoListResponse(
        items=[TodoResponse.model_validate(t) for t in todos],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("", response_model=TodoResponse, status_code=201)
async def create_todo(body: TodoCreate, current_user: CurrentUser, db: DBSession) -> TodoResponse:
    service = TodoService(db)
    todo = await service.create(current_user.id, body)
    return TodoResponse.model_validate(todo)


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DBSession) -> TodoResponse:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    return TodoResponse.model_validate(todo)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: uuid.UUID, body: TodoUpdate, current_user: CurrentUser, db: DBSession
) -> TodoResponse:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    updated = await service.update(todo, body)
    return TodoResponse.model_validate(updated)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(todo_id: uuid.UUID, current_user: CurrentUser, db: DBSession) -> None:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    await service.delete(todo)
