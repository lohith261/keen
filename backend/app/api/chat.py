"""Pipeline chat endpoint — RAG-style Q&A over completed engagement data."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import AuthUser, get_current_user
from app.config import get_settings
from app.dependencies import get_session
from app.models.agent_run import AgentRun
from app.models.engagement import Engagement
from app.models.finding import Finding

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatSource(BaseModel):
    system: str
    label: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


# ── Human-readable source labels ──────────────────────────────────────────────

SOURCE_LABELS: dict[str, str] = {
    "salesforce": "Salesforce CRM",
    "hubspot": "HubSpot",
    "netsuite": "NetSuite ERP",
    "quickbooks": "QuickBooks",
    "crunchbase": "Crunchbase",
    "bloomberg": "Bloomberg Terminal",
    "capiq": "S&P Capital IQ",
    "pitchbook": "PitchBook",
    "sales_navigator": "LinkedIn Sales Navigator",
    "zoominfo": "ZoomInfo",
    "marketo": "Marketo",
    "dynamics": "Microsoft Dynamics",
    "sap": "SAP ERP",
    "oracle": "Oracle Cloud ERP",
    "datasite": "Datasite VDR",
    "intralinks": "Intralinks VDR",
    "tegus": "Tegus",
    "third_bridge": "Third Bridge",
    "demo": "Demo Data",
    "document": "Uploaded Documents",
    "analysis": "Analysis Agent",
    "delivery": "Delivery Agent",
}


def _label(source: str | None) -> str:
    if not source:
        return "KEEN Pipeline"
    return SOURCE_LABELS.get(source.lower(), source.replace("_", " ").title())


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(engagement: Engagement, findings: list[Finding]) -> str:
    """Serialize engagement pipeline data + findings into a prompt context block."""
    lines: list[str] = []

    # Engagement metadata
    lines.append(f"## Engagement: {engagement.company_name}")
    if engagement.config.get("target_company"):
        lines.append(f"Target Company: {engagement.config['target_company']}")
    if engagement.config.get("pe_firm"):
        lines.append(f"PE Firm: {engagement.config['pe_firm']}")
    lines.append("")

    # Findings — the primary data source
    if findings:
        lines.append("## Findings")
        for f in findings:
            severity = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            source_label = _label(f.source_system)
            lines.append(
                f"[{severity.upper()}] [{source_label}] {f.title}"
            )
            if f.description:
                lines.append(f"  {f.description}")
            # Include structured data fields if present
            if f.data:
                for k, v in f.data.items():
                    if v and k not in ("raw", "html", "screenshot"):
                        lines.append(f"  {k}: {v}")
            lines.append("")

    # Pipeline data — raw source extractions
    pipeline_data = engagement.config.get("pipeline_data", {})
    research_state = pipeline_data.get("research", {})

    if research_state:
        lines.append("## Raw Source Data")
        for key, value in research_state.items():
            if not isinstance(value, dict):
                continue
            source_name = key.replace("data_", "").replace("_", " ").title()
            lines.append(f"### {source_name}")
            # Flatten top-level keys, skip large blobs
            for k, v in value.items():
                if isinstance(v, (str, int, float, bool)) and v:
                    lines.append(f"  {k}: {v}")
                elif isinstance(v, list) and v:
                    preview = v[:5]
                    lines.append(f"  {k}: {preview}")
            lines.append("")

    # Delivery summary if available
    delivery = pipeline_data.get("delivery", {})
    exec_summary = (
        delivery
        .get("finalize_delivery", {})
        .get("deliverables", {})
        .get("executive_summary", {})
    )
    if exec_summary:
        lines.append("## Executive Summary")
        if exec_summary.get("recommendation"):
            lines.append(f"Recommendation: {exec_summary['recommendation']}")
        if exec_summary.get("recommendation_rationale"):
            lines.append(f"Rationale: {exec_summary['recommendation_rationale']}")
        if exec_summary.get("key_findings"):
            lines.append("Key Findings:")
            for kf in exec_summary["key_findings"]:
                lines.append(f"  - {kf}")
        lines.append("")

    return "\n".join(lines)


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@router.post("/{engagement_id}/chat", response_model=ChatResponse)
async def chat_with_pipeline(
    engagement_id: UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
) -> ChatResponse:
    """
    Answer questions about a completed engagement using its pipeline data and findings.
    Each answer includes source attribution.
    """
    # Load engagement
    engagement = await db.get(Engagement, engagement_id)
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.user_id and engagement.user_id != current_user.sub:
        raise HTTPException(status_code=403, detail="Not authorised")

    # Load findings
    result = await db.execute(
        select(Finding)
        .join(AgentRun)
        .where(AgentRun.engagement_id == engagement_id)
        .order_by(Finding.severity.desc(), Finding.created_at.asc())
    )
    findings = list(result.scalars().all())

    if not findings and not engagement.config.get("pipeline_data"):
        raise HTTPException(
            status_code=400,
            detail="No pipeline data available yet. Run the pipeline first.",
        )

    context = _build_context(engagement, findings)

    # Build source list for the response
    source_systems = sorted({
        _label(f.source_system) for f in findings if f.source_system
    })

    settings = get_settings()

    # Try Anthropic first, fall back to OpenAI
    answer = ""
    if settings.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            response = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                system=(
                    "You are KEEN's pipeline analyst. You answer questions about a completed "
                    "due diligence engagement using only the data provided below. "
                    "Always cite the source system for every claim you make, using the format [Source: Name]. "
                    "If the data doesn't contain enough information to answer, say so clearly. "
                    "Be concise, precise, and professional.\n\n"
                    "PIPELINE DATA:\n"
                    f"{context}"
                ),
                messages=[{"role": "user", "content": body.message}],
            )
            answer = response.content[0].text
        except Exception as exc:
            logger.warning("Anthropic chat failed: %s", exc)

    if not answer and settings.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are KEEN's pipeline analyst. Answer questions about the due diligence "
                            "engagement using only the data below. Always cite [Source: Name] for every claim. "
                            "PIPELINE DATA:\n" + context
                        ),
                    },
                    {"role": "user", "content": body.message},
                ],
                max_tokens=1024,
            )
            answer = response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("OpenAI chat fallback failed: %s", exc)

    if not answer:
        raise HTTPException(
            status_code=503,
            detail="No LLM available to answer the question. Check API keys.",
        )

    return ChatResponse(answer=answer, sources=source_systems)
