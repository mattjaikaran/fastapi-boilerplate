import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_keys.model import APIKey
from app.api.api_keys.schemas import APIKeyCreate
from app.core.exceptions import ForbiddenError, NotFoundError

_KEY_PREFIX_LEN = 8
_KEY_BYTES = 32


def _generate_key() -> tuple[str, str, str]:
    """Returns (raw_key, prefix, sha256_hash)."""
    raw = secrets.token_urlsafe(_KEY_BYTES)
    prefix = raw[:_KEY_PREFIX_LEN]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash


class APIKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, user_id: uuid.UUID, data: APIKeyCreate
    ) -> tuple[APIKey, str]:
        raw_key, prefix, key_hash = _generate_key()
        api_key = APIKey(
            user_id=user_id,
            org_id=data.org_id,
            name=data.name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=data.scopes,
            expires_at=data.expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key, raw_key

    async def get_by_raw_key(self, raw_key: str) -> APIKey | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        api_key = result.scalar_one_or_none()
        if api_key and api_key.is_active:
            await self.db.execute(
                update(APIKey)
                .where(APIKey.id == api_key.id)
                .values(last_used_at=datetime.now(UTC))
            )
        return api_key

    async def list_for_user(
        self, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[APIKey], int]:
        q = select(APIKey).where(APIKey.user_id == user_id)
        total = (
            await self.db.execute(select(func.count()).select_from(q.subquery()))
        ).scalar_one()
        items = list(
            (
                await self.db.execute(
                    q.order_by(APIKey.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total

    async def revoke(self, api_key_id: uuid.UUID, user_id: uuid.UUID) -> None:
        api_key = await self.db.get(APIKey, api_key_id)
        if not api_key or api_key.user_id != user_id:
            raise NotFoundError(detail="API key not found")
        if api_key.revoked_at is not None:
            raise ForbiddenError(detail="API key is already revoked")
        api_key.revoked_at = datetime.now(UTC)
        self.db.add(api_key)
        await self.db.flush()

    async def delete(self, api_key_id: uuid.UUID, user_id: uuid.UUID) -> None:
        api_key = await self.db.get(APIKey, api_key_id)
        if not api_key or api_key.user_id != user_id:
            raise NotFoundError(detail="API key not found")
        await self.db.delete(api_key)
        await self.db.flush()
