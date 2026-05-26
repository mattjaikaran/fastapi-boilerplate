import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.files.model import FileUpload
from app.config.settings import settings
from app.core.exceptions import ForbiddenError, NotFoundError, UnprocessableError


class StorageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upload(self, file: UploadFile, user_id: uuid.UUID) -> FileUpload:
        if not file.filename:
            raise UnprocessableError(detail="Filename is required")

        # Validate size
        content = await file.read()
        if len(content) > settings.upload_max_size_bytes:
            raise UnprocessableError(
                detail=f"File too large. Max size: {settings.UPLOAD_MAX_SIZE_MB}MB"
            )

        file_id = uuid.uuid4()
        ext = Path(file.filename).suffix
        stored_name = f"{file_id}{ext}"

        if settings.STORAGE_DRIVER == "s3":
            url = await self._upload_s3(content, stored_name, file.content_type or "application/octet-stream")
            storage_path = stored_name
        else:
            storage_path = await self._upload_local(content, stored_name)
            url = None

        record = FileUpload(
            id=file_id,
            user_id=user_id,
            filename=stored_name,
            original_filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
            storage_path=storage_path,
            storage_driver=settings.STORAGE_DRIVER,
            url=url,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_id(self, file_id: uuid.UUID, user_id: uuid.UUID) -> FileUpload:
        result = await self.db.get(FileUpload, file_id)
        if not result:
            raise NotFoundError(detail=f"File {file_id} not found")
        if result.user_id != user_id:
            raise ForbiddenError()
        return result

    async def delete(self, file_id: uuid.UUID, user_id: uuid.UUID) -> None:
        record = await self.get_by_id(file_id, user_id)

        if record.storage_driver == "s3":
            await self._delete_s3(record.storage_path)
        else:
            self._delete_local(record.storage_path)

        await self.db.delete(record)
        await self.db.flush()

    async def _upload_local(self, content: bytes, filename: str) -> str:
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_dir / filename
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)
        return str(path)

    def _delete_local(self, path: str) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()

    async def _upload_s3(self, content: bytes, key: str, content_type: str) -> str:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        ) as s3:
            await s3.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        endpoint = settings.AWS_S3_ENDPOINT_URL or f"https://s3.{settings.AWS_REGION}.amazonaws.com"
        return f"{endpoint}/{settings.AWS_S3_BUCKET}/{key}"

    async def _delete_s3(self, key: str) -> None:
        import aioboto3

        session = aioboto3.Session()
        async with session.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
        ) as s3:
            await s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
