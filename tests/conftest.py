import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.main import create_app
from app.models.base import Base

# Use test DB (same URL in test mode)
TEST_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.config.database import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def user(db: AsyncSession):
    from app.api.users.service import UserService
    from app.api.users.schemas import UserCreate

    service = UserService(db)
    user = await service.create(
        UserCreate(email="test@example.com", password="password123", first_name="Test", last_name="User")
    )
    user.is_email_verified = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    from app.api.users.model import UserRole
    from app.api.users.service import UserService
    from app.api.users.schemas import UserCreate

    service = UserService(db)
    user = await service.create(
        UserCreate(email="admin@example.com", password="password123", first_name="Admin", last_name="User")
    )
    user.role = UserRole.admin
    user.is_email_verified = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, user) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": user.email, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user) -> dict[str, str]:
    response = await client.post("/api/auth/login", json={"email": admin_user.email, "password": "password123"})
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
