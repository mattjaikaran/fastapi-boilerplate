# Feature Generation Guide

Every module in this boilerplate follows the same 5-file pattern.
Adding a new domain entity takes ~5 minutes manually or ~10 seconds with the generator.

---

## Quick start — generator

```bash
# Scaffold a new module
uv run python scripts/generate_module.py <name>

# Examples
uv run python scripts/generate_module.py payments
uv run python scripts/generate_module.py subscription_plans
uv run python scripts/generate_module.py comment   # generates a "comments" table

# Preview without writing
uv run python scripts/generate_module.py payments --dry-run

# Skip model.py (no DB table, e.g. a proxy / aggregation module)
uv run python scripts/generate_module.py stats --no-model
```

Or via Make:

```bash
make generate MODULE=payments
```

---

## What gets generated

```
app/api/<name>/
├── __init__.py        # empty package marker
├── model.py           # SQLAlchemy ORM model (BaseModel + user FK)
├── schemas.py         # Pydantic request/response schemas
├── service.py         # async DB layer (list / get / create / update / delete)
└── router.py          # FastAPI router with full CRUD endpoints
```

---

## Manual steps after generation

### 1. Customise `model.py`

Add your columns, enums, and relationships.

```python
# app/api/payments/model.py
class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class Payment(BaseModel):
    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(...)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), ...)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

### 2. Register the model in `app/models/__init__.py`

```python
def register_all_models() -> None:
    ...
    from app.api.payments.model import Payment  # noqa: F401
```

### 3. Register the router in `app/api/router.py`

```python
from app.api.payments.router import router as payments_router
...
api_router.include_router(payments_router)
```

### 4. Create and run the migration

```bash
make migration msg="add payments table"
make migrate-local
```

---

## Module anatomy

### `model.py` — ORM layer

- Inherit from `BaseModel` (adds `id`, `created_at`, `updated_at`)
- Use `SoftDeleteMixin` for soft-delete (`deleted_at` column)
- All FK columns use `UUID(as_uuid=True)`

```python
from app.models.base import BaseModel, SoftDeleteMixin

class Payment(SoftDeleteMixin, BaseModel):
    __tablename__ = "payments"
```

### `schemas.py` — Pydantic schemas

Convention:

| Schema | Purpose |
|---|---|
| `<Name>Base` | shared fields (no id/timestamps) |
| `<Name>Create` | POST body |
| `<Name>Update` | PATCH body (all fields `| None`) |
| `<Name>Response` | GET response (`model_config = {"from_attributes": True}`) |
| `<Name>ListResponse` | paginated list |

### `service.py` — business logic

- Constructor takes `db: AsyncSession`
- Returns ORM models; routers convert to Pydantic via `model_validate`
- Use `await self.db.flush()` + `await self.db.refresh(item)` after mutations
- Raise `NotFoundError`, `ConflictError`, `ForbiddenError` from `app.core.exceptions`

### `router.py` — HTTP layer

- `prefix="/<route>"`, `tags=["<tag>"]`
- Inject `current_user: CurrentUser` and `db: DBSession` via `Depends`
- Standard status codes: `200` list/get, `201` create, `204` delete
- Use `Query(1, ge=1)` for pagination params

---

## Conventions checklist

- [ ] Model inherits `BaseModel` (gets `id`, `created_at`, `updated_at`)
- [ ] Model registered in `register_all_models()`
- [ ] Router registered in `app/api/router.py`
- [ ] All endpoints require `CurrentUser` (or `AdminUser` for admin routes)
- [ ] Service raises typed exceptions (`NotFoundError`, `ConflictError`, etc.)
- [ ] Alembic migration created and tested
- [ ] Integration tests added under `tests/integration/test_<name>.py`

---

## Adding admin views (sqladmin)

Register in `app/admin/views.py`:

```python
from app.api.payments.model import Payment

class PaymentAdmin(ModelView, model=Payment):
    column_list = [Payment.id, Payment.user_id, Payment.amount_cents, Payment.status]
    column_searchable_list = [Payment.status]
```

Then register the view in `app/admin/setup.py`.

---

## Adding Celery tasks

Place tasks under `app/workers/tasks/<name>.py`:

```python
from app.workers.celery_app import celery_app

@celery_app.task(queue="default")
def process_payment(payment_id: str) -> None:
    ...
```

---

## Adding WebSocket push for a module

After creating a notification inside your service, push to the user's live connection:

```python
from app.api.ws.manager import ws_manager

await ws_manager.send(user_id, {
    "event": "payment.completed",
    "data": {"payment_id": str(payment.id), "amount": payment.amount_cents},
})
```

This uses the singleton `ConnectionManager` shared across the process.
