# KEEN — Product Gap Tasks

Gaps identified by critical evaluation against McKinsey/BCG/Bain DD methodology.
These represent what separates KEEN from a true institutional-grade DD platform.

## ✅ Completed (P4 / P5 / P7 / P8 backend + frontend)

The following were fully implemented and pushed to main:

| What | Details |
|---|---|
| Backend models | `primary_research.py`, `external_record.py`, `legal_finding.py`, `technical_dd.py` |
| Backend services | `primary_research_service.py` (themes + sentiment), `verification_service.py` (confidence scoring) |
| Integrations | `courtlistener.py`, `uspto.py`, `bank_statement_parser.py`, `github/client.py` |
| API routes | `/primary-research`, `/external-records`, `/legal-findings`, `/technical-dd` mounted at `/engagements/{id}/` |
| Contract analyzer | `contract_analyzer_service.py` — 5 clause types, date extraction, risk scoring |
| Technical DD service | `technical_dd_service.py` wrapping `GitHubAnalyzer` |
| Alembic migration | `007_add_p4_p5_p7_p8_tables.py` — 4 new tables + enum types |
| Engagement model | 4 new relationships wired with cascade delete |
| Frontend panels | `CommercialDDPanel.tsx`, `ExternalVerificationPanel.tsx`, `TechnicalDDPanel.tsx` |
| Frontend wiring | Dashboard.tsx — 3 new tabs (INTERVIEWS / VERIFY / TECH DD) + panel rendering |
| API client | `primaryResearchApi`, `externalRecordsApi`, `legalFindingsApi`, `technicalDDApi` in `apiClient.ts` |

---

## P4 — Commercial DD (Primary Research)

- [x] **P4-1** Build customer interview workflow — structured templates, scheduling, response capture
- [x] **P4-2** Channel check module — interview distributors/resellers, not just internal CRM data
- [x] **P4-3** Win/loss analysis from external sources — competitor customer references
- [x] **P4-4** Independent market sizing — connect to third-party market research APIs (Statista, IBISWorld)
- [ ] **P4-5** Pricing power analysis — benchmark target's pricing vs market alternatives

---

## P5 — External Data Verification

- [x] **P5-1** Bank statement reconciliation — upload and parse bank statements as independent source
- [ ] **P5-2** Tax return vs management accounts comparison — flag discrepancies
- [x] **P5-3** Public court/litigation records search — CourtListener REST API integrated
- [ ] **P5-4** UCC filings search — check for undisclosed liens and encumbrances
- [x] **P5-5** Patent/IP ownership verification — USPTO API integrated, detect ownership gaps
- [ ] **P5-6** Property/asset records — cross-check declared assets against public records
- [x] **P5-7** Confidence decay scoring — source independence + confidence score computed per-finding

---

## P6 — Financial DD Depth

- [ ] **P6-1** Deferred revenue and backlog quality analysis
- [ ] **P6-2** Customer concentration analysis with contract review (top 10 customers as % of ARR)
- [ ] **P6-3** Working capital normalisation model
- [ ] **P6-4** Detect when multiple internal systems (Salesforce + NetSuite) tell the same constructed story — require external corroboration before flagging as clean

---

## P7 — Legal & IP DD

- [ ] **P7-1** IP ownership audit — who actually owns the code/patents (employees vs company)
- [x] **P7-2** Change-of-control clause scanner — parse customer contracts for CoC triggers, non-compete, IP ownership, regulatory, litigation clauses
- [x] **P7-3** Outstanding litigation search and risk scoring — CourtListener + risk level per finding
- [x] **P7-4** Employment agreement and non-compete review — NLP clause scanner covers non-compete patterns
- [ ] **P7-5** Regulatory exposure assessment by industry vertical

---

## P8 — Technical DD

- [x] **P8-1** Code quality and tech debt analysis — GitHub API integration, language breakdown, contributor analysis
- [x] **P8-2** Security posture scan — CVEs, dependency vulnerabilities detected via GitHub API
- [ ] **P8-3** Architecture scalability assessment — infrastructure cost modelling
- [x] **P8-4** Engineering team health — bus factor, contributor concentration, commit velocity, health score (0–100)

---

## P9 — Industry-Specific Frameworks

- [ ] **P9-1** SaaS DD framework — ARR, NRR, CAC payback, magic number, rule of 40
- [ ] **P9-2** Manufacturing DD framework — capacity utilisation, COGS breakdown, supply chain concentration
- [ ] **P9-3** Healthcare DD framework — reimbursement risk, regulatory compliance, payer mix
- [ ] **P9-4** Marketplace DD framework — take rate, GMV quality, liquidity, supply/demand balance
- [ ] **P9-5** Auto-detect company vertical and apply relevant framework at engagement creation

---

## P10 — Human-in-the-Loop & Confidence

- [ ] **P10-1** Mandatory analyst validation checkpoints before report generation
- [ ] **P10-2** Confidence scoring system — every finding rated by source count + source independence
- [ ] **P10-3** "Blind spots" section in report — explicit list of what KEEN could not verify
- [ ] **P10-4** Escalation triggers — auto-flag findings that require human expert review before proceeding
- [ ] **P10-5** Audit trail of what was and wasn't checked — not just what was found

---

## P11 — Synergy & Integration Thesis

- [ ] **P11-1** Post-acquisition 100-day plan template generator
- [ ] **P11-2** Synergy modelling — revenue synergies, cost synergies, one-time integration costs
- [ ] **P11-3** Integration risk scoring — culture, tech stack, key person dependencies
- [ ] **P11-4** Retention risk analysis — which employees are likely to leave post-acquisition

---

## P12 — Positioning & Trust Layer

- [ ] **P12-1** Reframe product positioning — "gives analysts a running start" not "replaces DD"
- [ ] **P12-2** Add explicit disclaimer/scope section to every generated report
- [ ] **P12-3** Source independence rating system — flag when all sources are seller-controlled
- [ ] **P12-4** "What we didn't check" appendix in every IC memo

---

## Notes

- **Highest priority gaps**: P5 (external verification) and P10 (human-in-the-loop) — these are the ones that create false confidence risk
- **Quickest wins**: P6-1, P6-2 (financial depth), P8-1 (GitHub integration), P9-1 (SaaS framework auto-detect)
- **Core positioning risk**: Without P5 and P10, KEEN could produce a clean report on manipulated data and look authoritative doing it
