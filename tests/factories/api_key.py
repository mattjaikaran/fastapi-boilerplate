import hashlib
import secrets
import uuid
from datetime import UTC, datetime

import factory
from factory import Faker

from app.api.api_keys.model import APIKey


def _make_key_hash() -> str:
    raw = secrets.token_urlsafe(32)
    return hashlib.sha256(raw.encode()).hexdigest()


class APIKeyFactory(factory.Factory):
    class Meta:
        model = APIKey

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    org_id = None
    name = Faker("word")
    key_prefix = factory.LazyFunction(lambda: secrets.token_urlsafe(6)[:8])
    key_hash = factory.LazyFunction(_make_key_hash)
    scopes = factory.LazyFunction(list)
    expires_at = None
    last_used_at = None
    revoked_at = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
