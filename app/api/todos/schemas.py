import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.api.todos.model import TodoPriority


class TodoCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    priority: TodoPriority = TodoPriority.medium
    due_at: datetime | None = None


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_completed: bool | None = None
    priority: TodoPriority | None = None
    due_at: datetime | None = None


class TodoBulkUpdate(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    is_completed: bool | None = None
    priority: TodoPriority | None = None


class TodoBulkDelete(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class TodoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    is_completed: bool
    priority: TodoPriority
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TodoListResponse(BaseModel):
    items: list[TodoResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TodoStatsResponse(BaseModel):
    total: int
    completed: int
    pending: int
    overdue: int
    due_today: int
    by_priority: dict[str, int]
