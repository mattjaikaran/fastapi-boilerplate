import uuid
from datetime import UTC, datetime

import factory
from factory import Faker

from app.api.notifications.model import Notification, NotificationType


class NotificationFactory(factory.Factory):
    class Meta:
        model = Notification

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    title = Faker("sentence", nb_words=4)
    body = Faker("paragraph")
    type = NotificationType.info
    is_read = False
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
