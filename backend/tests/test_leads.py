"""Tests for lead capture endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient):
    """POST /api/v1/leads should create a lead and return 201."""
    payload = {
        "name": "Jane Smith",
        "email": "jane@acmecapital.com",
        "company": "Acme Capital Partners",
        "aum_range": "$100M-$500M",
        "message": "Interested in piloting for our next deal.",
    }
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Smith"
    assert data["email"] == "jane@acmecapital.com"
    assert data["company"] == "Acme Capital Partners"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_lead_minimal(client: AsyncClient):
    """POST /api/v1/leads with only required fields."""
    payload = {"name": "John", "email": "john@example.com"}
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["company"] is None
    assert data["aum_range"] is None


@pytest.mark.asyncio
async def test_create_lead_missing_email_returns_422(client: AsyncClient):
    """POST /api/v1/leads without email should return 422."""
    payload = {"name": "Jane Smith"}
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_missing_name_returns_422(client: AsyncClient):
    """POST /api/v1/leads without name should return 422."""
    payload = {"email": "jane@example.com"}
    response = await client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_leads(client: AsyncClient):
    """GET /api/v1/leads should return a list."""
    # Create two leads
    await client.post("/api/v1/leads", json={"name": "A", "email": "a@test.com"})
    await client.post("/api/v1/leads", json={"name": "B", "email": "b@test.com"})

    response = await client.get("/api/v1/leads")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_get_lead_by_id(client: AsyncClient):
    """GET /api/v1/leads/{id} should return the lead."""
    create_response = await client.post(
        "/api/v1/leads", json={"name": "C", "email": "c@test.com"}
    )
    lead_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/leads/{lead_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "c@test.com"


@pytest.mark.asyncio
async def test_get_lead_not_found(client: AsyncClient):
    """GET /api/v1/leads/{invalid_id} should return 404."""
    response = await client.get("/api/v1/leads/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
