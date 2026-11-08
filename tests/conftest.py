import json
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response
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


@pytest.fixture(autouse=True)
def _fresh_redis_pool():
    """Each test runs on its own event loop: drop the cached Redis pool."""
    from app.services import cache

    cache._redis_pool = None
    yield
    cache._redis_pool = None


@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(setup_db) -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
        await session.rollback()
    # Tests commit; empty every table so each test starts from a clean DB.
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


async def _unwrap_envelope(response: Response) -> None:
    """Expose the payload of the response envelope as the JSON body."""
    await response.aread()
    try:
        body = response.json()
    except ValueError:
        return
    if isinstance(body, dict) and {"success", "data", "requestId"} <= body.keys():
        response._content = json.dumps(body["data"]).encode()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    from app.config.database import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        event_hooks={"response": [_unwrap_envelope]},
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def user(db: AsyncSession):
    from app.api.users.schemas import UserCreate
    from app.api.users.service import UserService

    service = UserService(db)
    user = await service.create(
        UserCreate(
            email="test@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )
    )
    user.is_email_verified = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession):
    from app.api.users.model import UserRole
    from app.api.users.schemas import UserCreate
    from app.api.users.service import UserService

    service = UserService(db)
    user = await service.create(
        UserCreate(
            email="admin@example.com",
            password="password123",
            first_name="Admin",
            last_name="User",
        )
    )
    user.role = UserRole.admin
    user.is_email_verified = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, user) -> dict[str, str]:
    response = await client.post(
        "/api/auth/login", json={"email": user.email, "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, admin_user) -> dict[str, str]:
    response = await client.post(
        "/api/auth/login", json={"email": admin_user.email, "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
