"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    """GET /api/v1/health should return 200 with service info."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "keen-backend"
    assert "version" in data


@pytest.mark.asyncio
async def test_readiness_returns_200(client: AsyncClient):
    """GET /api/v1/health/ready should return 200 with checks."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data
