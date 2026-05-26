import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.jobs.model import BackgroundJob, JobStatus
from app.core.exceptions import NotFoundError

ALLOWED_TASKS: set[str] = {
    "app.workers.tasks.email.send_welcome",
    "app.workers.tasks.email.send_otp",
}


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def trigger(
        self,
        task_name: str,
        name: str,
        args: list,
        kwargs: dict,
        triggered_by_id: uuid.UUID | None = None,
    ) -> BackgroundJob:
        from app.workers.celery_app import celery_app

        job = BackgroundJob(
            name=name,
            task_name=task_name,
            status=JobStatus.pending,
            args=args,
            kwargs=kwargs,
            triggered_by_id=triggered_by_id,
        )
        self.db.add(job)
        await self.db.flush()

        result = celery_app.send_task(task_name, args=args, kwargs=kwargs)
        job.celery_task_id = result.id
        job.status = JobStatus.running
        job.started_at = datetime.now(UTC)
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_by_id(self, job_id: uuid.UUID) -> BackgroundJob:
        job = await self.db.get(BackgroundJob, job_id)
        if not job:
            raise NotFoundError(detail=f"Job {job_id} not found")
        # Sync status from Celery if still running
        if job.status == JobStatus.running and job.celery_task_id:
            await self._sync_status(job)
        return job

    async def _sync_status(self, job: BackgroundJob) -> None:
        from celery.result import AsyncResult

        from app.workers.celery_app import celery_app

        result = AsyncResult(job.celery_task_id, app=celery_app)
        state = result.state
        if state == "SUCCESS":
            job.status = JobStatus.success
            job.result = (
                result.result
                if isinstance(result.result, dict)
                else {"value": str(result.result)}
            )
            job.completed_at = datetime.now(UTC)
        elif state == "FAILURE":
            job.status = JobStatus.failure
            job.error = str(result.result)
            job.completed_at = datetime.now(UTC)
        elif state == "REVOKED":
            job.status = JobStatus.revoked
            job.completed_at = datetime.now(UTC)
        self.db.add(job)
        await self.db.flush()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: JobStatus | None = None,
    ) -> tuple[list[BackgroundJob], int]:
        q = select(BackgroundJob)
        if status:
            q = q.where(BackgroundJob.status == status)
        total = (
            await self.db.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        items = list(
            (
                await self.db.execute(
                    q.order_by(BackgroundJob.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total
