"""Seed database with initial data."""
import asyncio

from app.api.users.model import UserRole
from app.api.users.schemas import UserCreate
from app.api.users.service import UserService
from app.config.database import async_session_factory
from app.config.settings import settings


async def seed() -> None:
    async with async_session_factory() as db:
        service = UserService(db)

        # Create superuser
        existing = await service.get_by_email(settings.FIRST_SUPERUSER_EMAIL)
        if not existing:
            user = await service.create(
                UserCreate(
                    email=settings.FIRST_SUPERUSER_EMAIL,
                    password=settings.FIRST_SUPERUSER_PASSWORD,
                    first_name="Super",
                    last_name="Admin",
                )
            )
            user.role = UserRole.superuser
            user.is_email_verified = True
            db.add(user)
            await db.commit()
            print(f"✓ Superuser created: {settings.FIRST_SUPERUSER_EMAIL}")
        else:
            print(f"  Superuser already exists: {settings.FIRST_SUPERUSER_EMAIL}")

        # Add more seed data here
        print("✓ Seed complete")


if __name__ == "__main__":
    asyncio.run(seed())
