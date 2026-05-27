"""
Locust load-test scenarios for the FastAPI boilerplate.

Run headless (CI / quick smoke):
    make test-load

Run with UI:
    uv run locust -f scripts/load_tests.py --host=http://localhost:8000

User classes:
    AuthUser      — register → login → profile reads
    TodoUser      — full todo lifecycle (create / list / toggle / delete)
    AdminUser     — admin-only list/search flows
    MixedUser     — realistic mix: auth + todo + notification reads
"""

from __future__ import annotations

import random
import string
import uuid

from locust import HttpUser, between, tag, task


# ── helpers ───────────────────────────────────────────────────────────────────

def _rand_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"load_{suffix}@example.com"


def _rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


# ── base user with JWT auth ───────────────────────────────────────────────────

class BaseAuthUser(HttpUser):
    abstract = True
    wait_time = between(0.5, 2.0)

    email: str
    password: str
    token: str | None = None
    user_id: str | None = None

    def on_start(self) -> None:
        self.email = _rand_email()
        self.password = "Loadtest1!"
        self._register_and_login()

    def _register_and_login(self) -> None:
        with self.client.post(
            "/api/auth/register",
            json={"email": self.email, "password": self.password},
            catch_response=True,
            name="/api/auth/register",
        ) as resp:
            if resp.status_code not in (200, 201, 409):
                resp.failure(f"Register failed: {resp.status_code}")
                return

        with self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": self.password},
            catch_response=True,
            name="/api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}


# ── scenario: auth & profile ──────────────────────────────────────────────────

class AuthUser(BaseAuthUser):
    """Registration → login → repeated profile & token-refresh reads."""

    weight = 2

    @task(5)
    @tag("auth", "profile")
    def get_profile(self) -> None:
        self.client.get("/api/users/me", headers=self.auth_headers, name="/api/users/me")

    @task(2)
    @tag("auth")
    def refresh_token(self) -> None:
        # Requires a refresh_token cookie / body — skip gracefully if unavailable
        self.client.post(
            "/api/auth/refresh",
            json={},
            headers=self.auth_headers,
            name="/api/auth/refresh",
        )

    @task(1)
    @tag("auth")
    def health_check(self) -> None:
        self.client.get("/api/health/live", name="/api/health/live")


# ── scenario: full todo lifecycle ────────────────────────────────────────────

class TodoUser(BaseAuthUser):
    """Create → list → toggle → stats → delete cycle."""

    weight = 4
    _todo_ids: list[str]

    def on_start(self) -> None:
        super().on_start()
        self._todo_ids = []

    @task(6)
    @tag("todos", "write")
    def create_todo(self) -> None:
        payload = {
            "title": f"Task {_rand_str()}",
            "description": f"Details about {_rand_str(12)}",
            "priority": random.choice(["low", "medium", "high"]),
        }
        with self.client.post(
            "/api/todos",
            json=payload,
            headers=self.auth_headers,
            catch_response=True,
            name="/api/todos POST",
        ) as resp:
            if resp.status_code == 201:
                self._todo_ids.append(resp.json()["id"])
            elif resp.status_code not in (200, 201):
                resp.failure(f"Create todo failed: {resp.status_code}")

    @task(8)
    @tag("todos", "read")
    def list_todos(self) -> None:
        self.client.get(
            "/api/todos",
            params={"page": 1, "page_size": 20},
            headers=self.auth_headers,
            name="/api/todos GET",
        )

    @task(3)
    @tag("todos", "read")
    def get_stats(self) -> None:
        self.client.get("/api/todos/stats", headers=self.auth_headers, name="/api/todos/stats")

    @task(4)
    @tag("todos", "write")
    def toggle_todo(self) -> None:
        if not self._todo_ids:
            return
        todo_id = random.choice(self._todo_ids)
        self.client.post(
            f"/api/todos/{todo_id}/toggle",
            headers=self.auth_headers,
            name="/api/todos/:id/toggle",
        )

    @task(3)
    @tag("todos", "read")
    def filter_todos(self) -> None:
        params = random.choice([
            {"completed": "false", "priority": "high"},
            {"completed": "true"},
            {"due_today": "true"},
            {"search": _rand_str(3)},
        ])
        self.client.get(
            "/api/todos",
            params=params,
            headers=self.auth_headers,
            name="/api/todos GET (filtered)",
        )

    @task(1)
    @tag("todos", "write")
    def delete_oldest_todo(self) -> None:
        if not self._todo_ids:
            return
        todo_id = self._todo_ids.pop(0)
        self.client.delete(
            f"/api/todos/{todo_id}",
            headers=self.auth_headers,
            name="/api/todos/:id DELETE",
        )

    @task(2)
    @tag("todos", "write")
    def bulk_update(self) -> None:
        if len(self._todo_ids) < 2:
            return
        ids = random.sample(self._todo_ids, min(3, len(self._todo_ids)))
        self.client.patch(
            "/api/todos/bulk",
            json={"ids": ids, "is_completed": True},
            headers=self.auth_headers,
            name="/api/todos/bulk PATCH",
        )


# ── scenario: notification reads ─────────────────────────────────────────────

class NotificationUser(BaseAuthUser):
    """List and mark-read notifications."""

    weight = 1

    @task(4)
    @tag("notifications")
    def list_notifications(self) -> None:
        self.client.get(
            "/api/notifications",
            params={"page": 1, "page_size": 10},
            headers=self.auth_headers,
            name="/api/notifications GET",
        )

    @task(1)
    @tag("notifications")
    def list_unread(self) -> None:
        self.client.get(
            "/api/notifications",
            params={"unread_only": "true"},
            headers=self.auth_headers,
            name="/api/notifications GET (unread)",
        )


# ── scenario: mixed realistic user ───────────────────────────────────────────

class MixedUser(BaseAuthUser):
    """Realistic mix: profile + todos + notifications + search."""

    weight = 3
    _todo_ids: list[str]

    def on_start(self) -> None:
        super().on_start()
        self._todo_ids = []
        # Pre-create 5 todos so subsequent tasks have something to work with
        for _ in range(5):
            self._create_todo_silent()

    def _create_todo_silent(self) -> None:
        resp = self.client.post(
            "/api/todos",
            json={"title": f"Seed {_rand_str()}", "priority": "medium"},
            headers=self.auth_headers,
            name="/api/todos POST (seed)",
        )
        if resp.status_code == 201:
            self._todo_ids.append(resp.json()["id"])

    @task(4)
    @tag("mixed", "profile")
    def profile(self) -> None:
        self.client.get("/api/users/me", headers=self.auth_headers, name="/api/users/me")

    @task(6)
    @tag("mixed", "todos")
    def list_todos(self) -> None:
        self.client.get(
            "/api/todos",
            params={"page": 1, "page_size": 10},
            headers=self.auth_headers,
            name="/api/todos GET",
        )

    @task(3)
    @tag("mixed", "todos")
    def create_and_complete(self) -> None:
        resp = self.client.post(
            "/api/todos",
            json={"title": f"Quick {_rand_str()}", "priority": "low"},
            headers=self.auth_headers,
            name="/api/todos POST",
        )
        if resp.status_code == 201:
            todo_id = resp.json()["id"]
            self._todo_ids.append(todo_id)
            self.client.post(
                f"/api/todos/{todo_id}/toggle",
                headers=self.auth_headers,
                name="/api/todos/:id/toggle",
            )

    @task(2)
    @tag("mixed", "notifications")
    def notifications(self) -> None:
        self.client.get(
            "/api/notifications",
            params={"page": 1, "page_size": 5},
            headers=self.auth_headers,
            name="/api/notifications GET",
        )

    @task(1)
    @tag("mixed", "search")
    def global_search(self) -> None:
        self.client.get(
            "/api/search",
            params={"q": _rand_str(3)},
            headers=self.auth_headers,
            name="/api/search GET",
        )

    @task(1)
    @tag("mixed", "health")
    def health(self) -> None:
        self.client.get("/api/health/live", name="/api/health/live")
