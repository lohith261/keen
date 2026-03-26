"""Tests for the RAG chat endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_no_data_returns_400(client: AsyncClient):
    """Chat should return 400 when engagement has no pipeline data or findings."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={"company_name": "Empty Corp"},
    )
    assert create_resp.status_code == 201
    eid = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/engagements/{eid}/chat",
        json={"message": "What are the key risks?"},
    )
    assert resp.status_code == 400
    assert "No pipeline data" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_chat_engagement_not_found(client: AsyncClient):
    """Chat on a non-existent engagement should return 404."""
    fake_id = str(uuid4())
    resp = await client.post(
        f"/api/v1/engagements/{fake_id}/chat",
        json={"message": "Hello"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_chat_returns_answer_with_anthropic(client: AsyncClient):
    """Chat endpoint should return answer and sources when Anthropic succeeds."""
    # Create an engagement with pipeline data so the 400 guard passes
    create_resp = await client.post(
        "/api/v1/engagements",
        json={
            "company_name": "Test Target",
            "config": {
                "pipeline_data": {
                    "research": {
                        "data_salesforce": {"revenue": "$50M", "deals": 120},
                    }
                }
            },
        },
    )
    eid = create_resp.json()["id"]

    mock_content = MagicMock()
    mock_content.text = "The revenue is $50M. [Source: Salesforce CRM]"
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    with patch("app.api.chat.get_settings") as mock_settings, \
         patch("anthropic.Anthropic", return_value=mock_client):
        settings = MagicMock()
        settings.anthropic_api_key = "test-key"
        settings.openai_api_key = ""
        settings.openrouter_api_key = ""
        mock_settings.return_value = settings

        resp = await client.post(
            f"/api/v1/engagements/{eid}/chat",
            json={"message": "What is the revenue?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_chat_no_llm_keys_returns_503(client: AsyncClient):
    """Chat should return 503 when no LLM keys are configured."""
    create_resp = await client.post(
        "/api/v1/engagements",
        json={
            "company_name": "No LLM Corp",
            "config": {"pipeline_data": {"research": {"data_sf": {"revenue": "100M"}}}},
        },
    )
    eid = create_resp.json()["id"]

    with patch("app.api.chat.get_settings") as mock_settings:
        settings = MagicMock()
        settings.anthropic_api_key = ""
        settings.openai_api_key = ""
        settings.openrouter_api_key = ""
        mock_settings.return_value = settings

        resp = await client.post(
            f"/api/v1/engagements/{eid}/chat",
            json={"message": "What are the risks?"},
        )

    assert resp.status_code == 503
    assert "No LLM" in resp.json()["detail"]
