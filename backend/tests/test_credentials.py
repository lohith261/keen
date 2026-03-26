"""Tests for the credentials store/list/delete endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


async def _create_engagement(client: AsyncClient, name: str = "Cred Corp") -> str:
    resp = await client.post("/api/v1/engagements", json={"company_name": name})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_store_credential(client: AsyncClient):
    """POST /credentials/{eid}/{system} should store and return credential metadata."""
    eid = await _create_engagement(client)

    resp = await client.post(
        f"/api/v1/credentials/{eid}/salesforce",
        json={
            "credential_type": "oauth",
            "credential_data": {
                "access_token": "tok_abc123",
                "instance_url": "https://na1.salesforce.com",
            },
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["system_name"] == "salesforce"
    assert data["credential_type"] == "oauth"
    assert "id" in data
    # Sensitive data must NOT be returned
    assert "access_token" not in data
    assert "credential_data" not in data


@pytest.mark.asyncio
async def test_list_credentials_empty(client: AsyncClient):
    """GET /credentials/{eid} should return empty list when nothing stored."""
    eid = await _create_engagement(client)

    resp = await client.get(f"/api/v1/credentials/{eid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["systems"] == []


@pytest.mark.asyncio
async def test_list_credentials_after_store(client: AsyncClient):
    """GET /credentials/{eid} should list systems that have been stored."""
    eid = await _create_engagement(client)

    # Store two systems
    await client.post(
        f"/api/v1/credentials/{eid}/salesforce",
        json={"credential_type": "api_key", "credential_data": {"api_key": "sk-sf"}},
    )
    await client.post(
        f"/api/v1/credentials/{eid}/hubspot",
        json={"credential_type": "oauth", "credential_data": {"token": "hs_tok"}},
    )

    resp = await client.get(f"/api/v1/credentials/{eid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    systems = {s["system_name"] for s in data["systems"]}
    assert "salesforce" in systems
    assert "hubspot" in systems


@pytest.mark.asyncio
async def test_store_credential_upserts(client: AsyncClient):
    """Storing credentials for the same system twice should replace (upsert)."""
    eid = await _create_engagement(client)

    await client.post(
        f"/api/v1/credentials/{eid}/salesforce",
        json={"credential_type": "api_key", "credential_data": {"api_key": "old"}},
    )
    await client.post(
        f"/api/v1/credentials/{eid}/salesforce",
        json={"credential_type": "oauth", "credential_data": {"token": "new"}},
    )

    resp = await client.get(f"/api/v1/credentials/{eid}")
    assert resp.status_code == 200
    data = resp.json()
    # Should still be only 1 entry (upserted)
    assert data["total"] == 1
    assert data["systems"][0]["credential_type"] == "oauth"


@pytest.mark.asyncio
async def test_delete_credential(client: AsyncClient):
    """DELETE /credentials/{eid}/{system} should remove stored credentials."""
    eid = await _create_engagement(client)

    await client.post(
        f"/api/v1/credentials/{eid}/netsuite",
        json={"credential_type": "api_key", "credential_data": {"key": "ns_key"}},
    )

    del_resp = await client.delete(f"/api/v1/credentials/{eid}/netsuite")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    list_resp = await client.get(f"/api/v1/credentials/{eid}")
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_credential_returns_404(client: AsyncClient):
    """DELETE for a system with no stored credentials should return 404."""
    eid = await _create_engagement(client)

    resp = await client.delete(f"/api/v1/credentials/{eid}/ghost_system")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_credentials_on_missing_engagement(client: AsyncClient):
    """Credential endpoints should 404 when engagement doesn't exist."""
    fake_id = str(uuid4())

    resp = await client.get(f"/api/v1/credentials/{fake_id}")
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/v1/credentials/{fake_id}/salesforce",
        json={"credential_type": "api_key", "credential_data": {"key": "x"}},
    )
    assert resp.status_code == 404
