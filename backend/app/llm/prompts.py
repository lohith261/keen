"""Prompt templates for all LLM integration points."""

# ── Research Agent: Extraction Planning ──────────────────

SYSTEM_PLAN_EXTRACTION = (
    "You are a private-equity due diligence data strategist. "
    "Given engagement parameters, select the most relevant data sources, "
    "prioritize them, and outline what to extract from each. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)

USER_PLAN_EXTRACTION = """\
Engagement details:
- Company: {company_name}
- Industry: {industry}
- Engagement type: {engagement_type}

Available data sources (id → info):
{sources_json}

Return a JSON object with:
{{
  "sources": [
    {{
      "source": "<source_id>",
      "name": "<display name>",
      "category": "<category>",
      "priority": <1-5, 1=highest>,
      "extractions": ["<extraction_type>", ...],
      "rationale": "<why this source matters for this engagement>"
    }}
  ],
  "reasoning": "<1-2 sentence overall strategy>"
}}

Select only the sources that are genuinely useful for this engagement. \
Prioritize sources that directly validate revenue, cost, and growth claims."""

# ── Analysis Agent: Cross-Referencing ────────────────────

SYSTEM_CROSS_REFERENCE = (
    "You are a financial analyst performing cross-source data validation "
    "for private-equity due diligence. Identify overlaps, correlations, "
    "and discrepancies across enterprise data sources. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)

USER_CROSS_REFERENCE = """\
Normalized data from {source_count} enterprise sources:
{data_summary}

Cross-reference the data and return:
{{
  "crm_erp_overlap": [
    {{
      "sources_compared": ["<source_a>", "<source_b>"],
      "metric": "<what is being compared>",
      "value_a": "<value from source a>",
      "value_b": "<value from source b>",
      "match_quality": <0.0-1.0>,
      "notes": "<explanation of match or discrepancy>"
    }}
  ],
  "marketing_revenue_correlation": [
    {{
      "sources_compared": ["<source_a>", "<source_b>"],
      "metric": "<what is being correlated>",
      "correlation_strength": <0.0-1.0>,
      "notes": "<explanation>"
    }}
  ],
  "market_data_benchmarks": [
    {{
      "metric": "<benchmark metric>",
      "internal_value": "<company's value>",
      "benchmark_value": "<industry/market value>",
      "percentile": <0-100>,
      "notes": "<how company compares>"
    }}
  ],
  "summary": "<brief overall assessment of data consistency>"
}}

Focus on the most material cross-references. \
Flag any data points where sources significantly disagree."""

# ── Analysis Agent: Finding Scoring ──────────────────────

SYSTEM_SCORE_FINDINGS = (
    "You are a due diligence quality assessor for a PE firm. "
    "Score each finding for reliability and materiality. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)

USER_SCORE_FINDINGS = """\
Score each finding from this due diligence engagement.

Findings:
{findings_json}

Return:
{{
  "scored_findings": [
    {{
      "finding_index": <0-based index>,
      "reliability_score": <0.0-1.0>,
      "impact_score": <0.0-1.0>,
      "confidence_justification": "<1-2 sentences>",
      "recommended_action": "accept" | "flag_for_review" | "investigate_further"
    }}
  ],
  "overall_confidence": <0.0-1.0>,
  "assessment_notes": "<brief overall quality assessment>"
}}

Consider: source quality, corroboration across sources, data recency, \
and materiality to the investment decision."""

# ── Delivery Agent: Executive Summary ────────────────────

SYSTEM_EXECUTIVE_SUMMARY = (
    "You are a senior private-equity advisor drafting a board-ready "
    "executive summary for a due diligence engagement. "
    "Write in clear, authoritative business prose. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)

USER_EXECUTIVE_SUMMARY = """\
Generate an executive summary for this due diligence engagement.

Company: {company_name}
Sources analyzed: {source_count}

Analysis results:
- Revenue variances: {revenue_variances}
- Cost variances: {cost_variances}
- Customer metrics: {customer_analysis}
- Market position: {market_analysis}
- Exceptions flagged: {exceptions}
- Cross-references: {cross_references}

Return:
{{
  "key_findings": [
    {{
      "title": "<concise finding title>",
      "description": "<2-3 sentence description with specific data>",
      "severity": "info" | "warning" | "critical",
      "supporting_data": "<key numbers>"
    }}
  ],
  "risk_assessment": "<overall risk level: low/moderate/high/critical with 2-3 paragraph justification>",
  "recommendation": "proceed" | "proceed_with_conditions" | "decline" | "insufficient_data",
  "recommendation_rationale": "<2-3 sentence rationale>"
}}

Include 3-7 key findings ordered by materiality. \
Be specific — cite data points, percentages, and dollar amounts where available."""

# ── Delivery Agent: Detailed Report Sections ─────────────

SYSTEM_DETAILED_REPORT = (
    "You are a PE due diligence report writer generating detailed sections "
    "of a board-ready due diligence report. Write in professional financial "
    "prose with specific data points and actionable insights. "
    "Respond with valid JSON only — no markdown fences, no commentary."
)

USER_DETAILED_REPORT = """\
Generate the following report sections for the {company_name} due diligence.

Sections to generate: {section_names}

Context:
- Executive summary: {executive_summary}
- Analysis data: {analysis_data}

Return:
{{
  "sections": [
    {{
      "section_title": "<section name>",
      "content": "<2-4 paragraphs of detailed analysis>",
      "data_points": [
        {{"metric": "<name>", "value": "<value>", "context": "<brief context>"}}
      ],
      "confidence_level": "high" | "medium" | "low"
    }}
  ]
}}

Be thorough but concise. Each section should stand on its own. \
Cite specific numbers from the analysis data where available."""
