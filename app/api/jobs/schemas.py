import uuid
from datetime import datetime

from pydantic import BaseModel

from app.api.jobs.model import JobStatus


class JobTriggerRequest(BaseModel):
    task_name: str
    name: str
    args: list = []
    kwargs: dict = {}


class JobResponse(BaseModel):
    id: uuid.UUID
    name: str
    task_name: str
    status: JobStatus
    args: list
    kwargs: dict
    result: dict | None
    error: str | None
    celery_task_id: str | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    triggered_by_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
