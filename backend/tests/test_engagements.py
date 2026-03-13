"""Tests for engagement CRUD and control endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_engagement(client: AsyncClient):
    """POST /api/v1/engagements should create an engagement."""
    payload = {
        "company_name": "Target Corp",
        "pe_firm": "Acme Capital",
        "deal_size": "$250M",
        "config": {
            "agents": ["research", "analysis", "delivery"],
            "systems": ["salesforce", "netsuite"],
        },
    }
    response = await client.post("/api/v1/engagements", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "Target Corp"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_engagements(client: AsyncClient):
    """GET /api/v1/engagements should return a list."""
    await client.post(
        "/api/v1/engagements",
        json={"company_name": "Test Co"},
    )
    response = await client.get("/api/v1/engagements")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_engagement_detail(client: AsyncClient):
    """GET /api/v1/engagements/{id} should return engagement with agent runs."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={"company_name": "Detail Co"},
    )
    eid = create_resp.json()["id"]

    response = await client.get(f"/api/v1/engagements/{eid}")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Detail Co"
    assert "agent_runs" in data


@pytest.mark.asyncio
async def test_update_draft_engagement(client: AsyncClient):
    """PATCH /api/v1/engagements/{id} should update a draft engagement."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={"company_name": "Update Co"},
    )
    eid = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/engagements/{eid}",
        json={"deal_size": "$500M"},
    )
    assert response.status_code == 200
    assert response.json()["deal_size"] == "$500M"


@pytest.mark.asyncio
async def test_start_engagement(client: AsyncClient):
    """POST /api/v1/engagements/{id}/start should set status to running."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={
            "company_name": "Start Co",
            "config": {"agents": ["research", "analysis"]},
        },
    )
    eid = create_resp.json()["id"]

    response = await client.post(f"/api/v1/engagements/{eid}/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert len(data["agent_runs"]) == 2


@pytest.mark.asyncio
async def test_pause_running_engagement(client: AsyncClient):
    """POST /api/v1/engagements/{id}/pause should pause a running engagement."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={"company_name": "Pause Co", "config": {"agents": ["research"]}},
    )
    eid = create_resp.json()["id"]

    # Start it first
    await client.post(f"/api/v1/engagements/{eid}/start")

    # Pause it
    response = await client.post(f"/api/v1/engagements/{eid}/pause")
    assert response.status_code == 200
    assert response.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_cannot_start_running_engagement(client: AsyncClient):
    """POST /api/v1/engagements/{id}/start should fail if already running."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={"company_name": "Double Start Co", "config": {"agents": ["research"]}},
    )
    eid = create_resp.json()["id"]

    await client.post(f"/api/v1/engagements/{eid}/start")
    response = await client.post(f"/api/v1/engagements/{eid}/start")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_engagement_not_found(client: AsyncClient):
    """GET /api/v1/engagements/{invalid_id} should return 404."""
    response = await client.get("/api/v1/engagements/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
