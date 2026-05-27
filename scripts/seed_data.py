"""Seed database with comprehensive dev data.

Creates:
  - 1 superuser (admin@example.com)
  - 3 regular users (alice, bob, charlie)
  - Todos for each user (mix of priorities, completion states, due dates)
  - 1 organization (Acme Corp) with all users as members
  - API key for alice

All users use password: password123
"""
import asyncio
from datetime import UTC, datetime, timedelta

from app.api.api_keys.schemas import APIKeyCreate
from app.api.api_keys.service import APIKeyService
from app.api.organizations.schemas import InviteMemberRequest, OrganizationCreate
from app.api.organizations.service import OrganizationService
from app.api.todos.model import TodoPriority
from app.api.todos.schemas import TodoCreate
from app.api.todos.service import TodoService
from app.api.users.model import UserRole
from app.api.users.schemas import UserCreate
from app.api.users.service import UserService
from app.config.database import async_session_factory
from app.config.settings import settings
from app.models.base import Base


async def seed() -> None:  # noqa: C901
    from app.config.database import engine
    from app.models import register_all_models

    register_all_models()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        user_service = UserService(db)

        # ── Superuser ─────────────────────────────────────────────────────────
        admin = await user_service.get_by_email(settings.FIRST_SUPERUSER_EMAIL)
        if not admin:
            admin = await user_service.create(
                UserCreate(
                    email=settings.FIRST_SUPERUSER_EMAIL,
                    password=settings.FIRST_SUPERUSER_PASSWORD,
                    first_name="Super",
                    last_name="Admin",
                )
            )
            admin.role = UserRole.superuser
            admin.is_email_verified = True
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print(f"✓ Superuser: {settings.FIRST_SUPERUSER_EMAIL}")
        else:
            print(f"  Superuser exists: {settings.FIRST_SUPERUSER_EMAIL}")

        # ── Regular users ─────────────────────────────────────────────────────
        seed_users = [
            ("alice@example.com", "Alice", "Smith"),
            ("bob@example.com", "Bob", "Jones"),
            ("charlie@example.com", "Charlie", "Brown"),
        ]
        created_users = []
        for email, first, last in seed_users:
            u = await user_service.get_by_email(email)
            if not u:
                u = await user_service.create(
                    UserCreate(email=email, password="password123", first_name=first, last_name=last)
                )
                u.is_email_verified = True
                db.add(u)
                await db.commit()
                await db.refresh(u)
                print(f"✓ User: {email}")
            else:
                print(f"  User exists: {email}")
            created_users.append(u)

        # ── Todos ─────────────────────────────────────────────────────────────
        alice = created_users[0]
        todo_service = TodoService(db)
        now = datetime.now(UTC)

        alice_todos = [
            TodoCreate(title="Set up CI/CD pipeline", priority=TodoPriority.high, due_at=now + timedelta(days=3)),
            TodoCreate(title="Write unit tests", priority=TodoPriority.high, due_at=now + timedelta(days=7)),
            TodoCreate(title="Review PR from Bob", priority=TodoPriority.medium, due_at=now + timedelta(days=1)),
            TodoCreate(title="Update API documentation", priority=TodoPriority.medium),
            TodoCreate(title="Refactor auth service", priority=TodoPriority.low, due_at=now - timedelta(days=2)),
            TodoCreate(title="Clean up old branches", priority=TodoPriority.low),
        ]
        existing_count = (await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(
                __import__("sqlalchemy", fromlist=["func"]).func.count()
            ).where(
                __import__("app.api.todos.model", fromlist=["Todo"]).Todo.user_id == alice.id
            )
        )).scalar_one()

        if existing_count == 0:
            for i, todo_data in enumerate(alice_todos):
                todo = await todo_service.create(alice.id, todo_data)
                if i < 2:  # mark first two as completed
                    todo.is_completed = True
                    db.add(todo)
            await db.commit()
            print(f"✓ Todos for alice ({len(alice_todos)} items)")
        else:
            print(f"  Todos for alice exist ({existing_count} items)")

        # ── Organization ──────────────────────────────────────────────────────
        from sqlalchemy import select as sa_select
        from app.api.organizations.model import Organization

        org_result = await db.execute(sa_select(Organization).where(Organization.slug == "acme-corp"))
        org = org_result.scalar_one_or_none()

        if not org:
            org_service = OrganizationService(db)
            org = await org_service.create(
                owner_id=admin.id,
                data=OrganizationCreate(name="Acme Corp", slug="acme-corp"),
            )
            await db.commit()
            await db.refresh(org)
            print(f"✓ Organization: {org.name}")

            # Add regular users as members
            for member_user in created_users:
                from app.api.organizations.model import OrgRole
                try:
                    await org_service.add_member(
                        org_id=org.id,
                        actor_id=admin.id,
                        data=InviteMemberRequest(user_id=member_user.id, role=OrgRole.member),
                    )
                except Exception:
                    pass
            await db.commit()
            print(f"✓ Added {len(created_users)} members to Acme Corp")
        else:
            print(f"  Organization exists: {org.name}")

        # ── API key for alice ─────────────────────────────────────────────────
        from app.api.api_keys.model import APIKey
        key_result = await db.execute(
            sa_select(APIKey).where(APIKey.user_id == alice.id)
        )
        existing_key = key_result.scalar_one_or_none()
        if not existing_key:
            api_key_service = APIKeyService(db)
            api_key, raw_key = await api_key_service.create(
                alice.id,
                APIKeyCreate(name="Dev API Key", scopes=["read", "write"]),
            )
            await db.commit()
            print(f"✓ API key for alice: {raw_key[:16]}...")
        else:
            print("  API key for alice exists")

    print("\n✓ Seed complete")
    print("\nCredentials (password: password123):")
    print(f"  Admin:   {settings.FIRST_SUPERUSER_EMAIL} / {settings.FIRST_SUPERUSER_PASSWORD}")
    for email, _, _ in seed_users:
        print(f"  User:    {email} / password123")
    print("\nDocs: http://localhost:8000/docs")
    print("Admin: http://localhost:8000/admin")


if __name__ == "__main__":
    asyncio.run(seed())
