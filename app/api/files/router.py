import uuid

from fastapi import APIRouter, UploadFile
from fastapi.responses import FileResponse as StarletteFileResponse

from app.api.auth.dependencies import CurrentUser
from app.api.files.schemas import FileResponse
from app.config.database import DBSession
from app.services.storage import StorageService

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    current_user: CurrentUser,
    db: DBSession,
) -> FileResponse:
    storage = StorageService(db)
    uploaded = await storage.upload(file=file, user_id=current_user.id)
    return FileResponse.model_validate(uploaded)


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(file_id: uuid.UUID, current_user: CurrentUser, db: DBSession) -> FileResponse:
    storage = StorageService(db)
    file_record = await storage.get_by_id(file_id, user_id=current_user.id)
    return FileResponse.model_validate(file_record)


@router.delete("/{file_id}", status_code=204)
async def delete_file(file_id: uuid.UUID, current_user: CurrentUser, db: DBSession) -> None:
    storage = StorageService(db)
    await storage.delete(file_id, user_id=current_user.id)
