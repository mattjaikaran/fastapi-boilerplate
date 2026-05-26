import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.users.model import User
from app.api.users.schemas import UserAdminUpdate, UserCreate, UserUpdate
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        result = await self.db.get(User, user_id)
        if not result or result.is_deleted:
            raise NotFoundError(detail=f"User {user_id} not found")
        return result

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        existing = await self.get_by_email(data.email)
        if existing:
            raise ConflictError(detail="Email already registered")

        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def admin_update(self, user: User, data: UserAdminUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def soft_delete(self, user: User) -> None:
        from datetime import UTC, datetime

        user.deleted_at = datetime.now(UTC)
        self.db.add(user)
        await self.db.flush()

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        query = select(User).where(User.deleted_at.is_(None))

        if search:
            query = query.where(
                User.email.ilike(f"%{search}%")
                | User.first_name.ilike(f"%{search}%")
                | User.last_name.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size)
        users = list((await self.db.execute(query)).scalars().all())

        return users, total
