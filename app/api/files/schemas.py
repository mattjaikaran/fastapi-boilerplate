import uuid
from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    url: str | None
    created_at: datetime
