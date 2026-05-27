import uuid
from datetime import UTC, datetime, timedelta

import factory
from factory import Faker

from app.api.todos.model import Todo, TodoPriority


class TodoFactory(factory.Factory):
    class Meta:
        model = Todo

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    title = Faker("sentence", nb_words=5)
    description = Faker("paragraph")
    is_completed = False
    priority = TodoPriority.medium
    due_at = None
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class CompletedTodoFactory(TodoFactory):
    is_completed = True


class OverdueTodoFactory(TodoFactory):
    is_completed = False
    due_at = factory.LazyFunction(lambda: datetime.now(UTC) - timedelta(days=1))


class HighPriorityTodoFactory(TodoFactory):
    priority = TodoPriority.high
