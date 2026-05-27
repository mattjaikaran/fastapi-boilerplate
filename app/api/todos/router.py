import uuid

from fastapi import APIRouter, Query

from app.api.auth.dependencies import CurrentUser
from app.api.todos.model import TodoPriority
from app.api.todos.schemas import (
    TodoBulkDelete,
    TodoBulkUpdate,
    TodoCreate,
    TodoListResponse,
    TodoResponse,
    TodoStatsResponse,
    TodoUpdate,
)
from app.api.todos.service import TodoService
from app.config.database import DBSession

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("/stats", response_model=TodoStatsResponse)
async def get_stats(current_user: CurrentUser, db: DBSession) -> TodoStatsResponse:
    service = TodoService(db)
    return await service.get_stats(current_user.id)


@router.get("", response_model=TodoListResponse)
async def list_todos(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    completed: bool | None = Query(default=None),
    priority: TodoPriority | None = Query(default=None),
    overdue: bool | None = Query(default=None),
    due_today: bool | None = Query(default=None),
) -> TodoListResponse:
    service = TodoService(db)
    todos, total = await service.list_todos(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        completed=completed,
        priority=priority,
        search=search,
        overdue=overdue,
        due_today=due_today,
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
async def create_todo(
    body: TodoCreate, current_user: CurrentUser, db: DBSession
) -> TodoResponse:
    service = TodoService(db)
    todo = await service.create(current_user.id, body)
    return TodoResponse.model_validate(todo)


@router.patch("/bulk", response_model=list[TodoResponse])
async def bulk_update(
    body: TodoBulkUpdate, current_user: CurrentUser, db: DBSession
) -> list[TodoResponse]:
    service = TodoService(db)
    todos = await service.bulk_update(current_user.id, body)
    return [TodoResponse.model_validate(t) for t in todos]


@router.post("/bulk-delete", status_code=200)
async def bulk_delete(
    body: TodoBulkDelete, current_user: CurrentUser, db: DBSession
) -> dict[str, int]:
    service = TodoService(db)
    deleted = await service.bulk_delete(current_user.id, body)
    return {"deleted": deleted}


@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> TodoResponse:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    return TodoResponse.model_validate(todo)


@router.post("/{todo_id}/toggle", response_model=TodoResponse)
async def toggle_todo(
    todo_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> TodoResponse:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    toggled = await service.toggle(todo)
    return TodoResponse.model_validate(toggled)


@router.patch("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: uuid.UUID, body: TodoUpdate, current_user: CurrentUser, db: DBSession
) -> TodoResponse:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    updated = await service.update(todo, body)
    return TodoResponse.model_validate(updated)


@router.delete("/{todo_id}", status_code=204)
async def delete_todo(
    todo_id: uuid.UUID, current_user: CurrentUser, db: DBSession
) -> None:
    service = TodoService(db)
    todo = await service.get_by_id(todo_id, current_user.id)
    await service.delete(todo)
