#!/usr/bin/env python3
"""
Module generator — scaffolds a new feature module under app/api/<name>/.

Usage:
    uv run python scripts/generate_module.py payments
    uv run python scripts/generate_module.py payments --no-model

Generated files:
    app/api/<name>/__init__.py
    app/api/<name>/model.py
    app/api/<name>/schemas.py
    app/api/<name>/service.py
    app/api/<name>/router.py

After generation:
    1. Register the model in app/models/__init__.py  (register_all_models)
    2. Register the router in app/api/router.py
    3. Create a migration:  make migration msg="add <name> table"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "app" / "api"

# ── templates ────────────────────────────────────────────────────────────────

INIT_TPL = ""

MODEL_TPL = """\
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class {Class}(BaseModel):
    __tablename__ = "{table}"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User")  # type: ignore[name-defined]  # noqa: F821


from app.api.users.model import User  # noqa: E402, F401
"""

SCHEMAS_TPL = """\
import uuid
from datetime import datetime

from pydantic import BaseModel


class {Class}Base(BaseModel):
    name: str
    description: str | None = None


class {Class}Create({Class}Base):
    pass


class {Class}Update(BaseModel):
    name: str | None = None
    description: str | None = None


class {Class}Response({Class}Base):
    model_config = {{"from_attributes": True}}

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class {Class}ListResponse(BaseModel):
    items: list[{Class}Response]
    total: int
    page: int
    page_size: int
    pages: int
"""

SERVICE_TPL = """\
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.{module}.model import {Class}
from app.api.{module}.schemas import {Class}Create, {Class}Update
from app.core.exceptions import NotFoundError


class {Class}Service:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: uuid.UUID, user_id: uuid.UUID) -> {Class}:
        item = await self.db.get({Class}, item_id)
        if not item or item.user_id != user_id:
            raise NotFoundError(detail="{Class} not found")
        return item

    async def list(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[{Class}], int]:
        query = select({Class}).where({Class}.user_id == user_id)
        total = (
            await self.db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar_one()
        items = list(
            (
                await self.db.execute(
                    query.order_by({Class}.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return items, total

    async def create(self, user_id: uuid.UUID, data: {Class}Create) -> {Class}:
        item = {Class}(user_id=user_id, **data.model_dump())
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def update(self, item: {Class}, data: {Class}Update) -> {Class}:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        self.db.add(item)
        await self.db.flush()
        await self.db.refresh(item)
        return item

    async def delete(self, item: {Class}) -> None:
        await self.db.delete(item)
        await self.db.flush()
"""

ROUTER_TPL = """\
import uuid

from fastapi import APIRouter, Query

from app.api.auth.dependencies import CurrentUser
from app.api.{module}.schemas import (
    {Class}Create,
    {Class}ListResponse,
    {Class}Response,
    {Class}Update,
)
from app.api.{module}.service import {Class}Service
from app.config.database import DBSession
from app.core.pagination.schemas import PaginationParams

router = APIRouter(prefix="/{route}", tags=["{tag}"])


@router.get("", response_model={Class}ListResponse)
async def list_{snake}(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> {Class}ListResponse:
    items, total = await {Class}Service(db).list(current_user.id, page, page_size)
    pages = (total + page_size - 1) // page_size
    return {Class}ListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("", response_model={Class}Response, status_code=201)
async def create_{snake}(
    data: {Class}Create,
    current_user: CurrentUser,
    db: DBSession,
) -> {Class}Response:
    return await {Class}Service(db).create(current_user.id, data)


@router.get("/{{{snake}_id}}", response_model={Class}Response)
async def get_{snake}(
    {snake}_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> {Class}Response:
    return await {Class}Service(db).get_by_id({snake}_id, current_user.id)


@router.patch("/{{{snake}_id}}", response_model={Class}Response)
async def update_{snake}(
    {snake}_id: uuid.UUID,
    data: {Class}Update,
    current_user: CurrentUser,
    db: DBSession,
) -> {Class}Response:
    svc = {Class}Service(db)
    item = await svc.get_by_id({snake}_id, current_user.id)
    return await svc.update(item, data)


@router.delete("/{{{snake}_id}}", status_code=204)
async def delete_{snake}(
    {snake}_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    svc = {Class}Service(db)
    item = await svc.get_by_id({snake}_id, current_user.id)
    await svc.delete(item)
"""

# ── helpers ──────────────────────────────────────────────────────────────────


def to_class(name: str) -> str:
    return "".join(part.capitalize() for part in name.replace("-", "_").split("_"))


def to_snake(name: str) -> str:
    return name.replace("-", "_").lower()


def to_table(name: str) -> str:
    s = to_snake(name)
    return s if s.endswith("s") else s + "s"


def to_route(name: str) -> str:
    return name.replace("_", "-").lower()


def to_tag(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").lower()


def write(path: Path, content: str, *, dry_run: bool) -> None:
    if dry_run:
        print(f"  [dry-run] would write {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  created  {path.relative_to(ROOT)}")


# ── main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new feature module.")
    parser.add_argument("name", help="Module name (snake_case), e.g. payments")
    parser.add_argument("--no-model", action="store_true", help="Skip model.py (no DB table)")
    parser.add_argument("--dry-run", action="store_true", help="Print files without writing")
    args = parser.parse_args()

    name = args.name.strip().lower().replace("-", "_")
    cls = to_class(name)
    snake = to_snake(name)
    table = to_table(name)
    route = to_route(name)
    tag = to_tag(name)

    target = API_DIR / name
    if target.exists() and not args.dry_run:
        print(f"Error: {target} already exists. Remove it first or pick a different name.")
        sys.exit(1)

    ctx = dict(Class=cls, module=name, snake=snake, table=table, route=route, tag=tag)

    print(f"\nGenerating module: {name}")
    write(target / "__init__.py", INIT_TPL, dry_run=args.dry_run)
    if not args.no_model:
        write(target / "model.py", MODEL_TPL.format(**ctx), dry_run=args.dry_run)
    write(target / "schemas.py", SCHEMAS_TPL.format(**ctx), dry_run=args.dry_run)
    write(target / "service.py", SERVICE_TPL.format(**ctx), dry_run=args.dry_run)
    write(target / "router.py", ROUTER_TPL.format(**ctx), dry_run=args.dry_run)

    print(f"""
Next steps:
  1. Edit app/api/{name}/model.py  — add your columns
  2. Register model in app/models/__init__.py inside register_all_models():
         from app.api.{name}.model import {cls}  # noqa: F401
  3. Register router in app/api/router.py:
         from app.api.{name}.router import router as {snake}_router
         api_router.include_router({snake}_router)
  4. Create migration:
         make migration msg="add {table} table"
  5. Run migration:
         make migrate-local
""")


if __name__ == "__main__":
    main()
