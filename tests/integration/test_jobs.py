import pytest
from httpx import AsyncClient


ALLOWED_TASK = "app.workers.tasks.email.send_welcome"


@pytest.mark.integration
async def test_trigger_job_requires_admin(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/jobs",
        json={"task_name": ALLOWED_TASK, "name": "Test Job"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.integration
async def test_trigger_job_as_admin(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/jobs",
        json={"task_name": ALLOWED_TASK, "name": "Welcome Email Job"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_name"] == ALLOWED_TASK
    assert data["name"] == "Welcome Email Job"
    assert data["status"] in ("pending", "running", "success", "failure")


@pytest.mark.integration
async def test_trigger_disallowed_task(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/jobs",
        json={"task_name": "os.system", "name": "Bad Job"},
        headers=admin_headers,
    )
    assert response.status_code == 403


@pytest.mark.integration
async def test_trigger_job_requires_auth(client: AsyncClient):
    response = await client.post(
        "/api/jobs",
        json={"task_name": ALLOWED_TASK, "name": "Unauth Job"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_list_jobs_as_admin(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/jobs",
        json={"task_name": ALLOWED_TASK, "name": "Listed Job"},
        headers=admin_headers,
    )
    response = await client.get("/api/jobs", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.integration
async def test_list_jobs_requires_admin(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/jobs", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.integration
async def test_get_job_by_id(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/jobs",
        json={"task_name": ALLOWED_TASK, "name": "Get By ID Job"},
        headers=admin_headers,
    )
    job_id = create.json()["id"]

    response = await client.get(f"/api/jobs/{job_id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == job_id
