import uuid

from fastapi import APIRouter

from app.api.auth.dependencies import AdminUser
from app.api.jobs.model import JobStatus
from app.api.jobs.schemas import JobListResponse, JobResponse, JobTriggerRequest
from app.api.jobs.service import ALLOWED_TASKS, JobService
from app.config.database import DBSession
from app.core.exceptions import ForbiddenError

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _svc(db: DBSession) -> JobService:
    return JobService(db)


@router.post("", response_model=JobResponse, status_code=201)
async def trigger_job(
    body: JobTriggerRequest,
    current_user: AdminUser,
    db: DBSession,
) -> JobResponse:
    if body.task_name not in ALLOWED_TASKS:
        raise ForbiddenError(
            detail=f"Task '{body.task_name}' is not in the allowed list"
        )
    job = await _svc(db).trigger(
        task_name=body.task_name,
        name=body.name,
        args=body.args,
        kwargs=body.kwargs,
        triggered_by_id=current_user.id,
    )
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def list_jobs(
    _: AdminUser,
    db: DBSession,
    page: int = 1,
    page_size: int = 20,
    status: JobStatus | None = None,
) -> JobListResponse:
    items, total = await _svc(db).list(page=page, page_size=page_size, status=status)
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(_: AdminUser, job_id: uuid.UUID, db: DBSession) -> JobResponse:
    job = await _svc(db).get_by_id(job_id)
    return JobResponse.model_validate(job)
