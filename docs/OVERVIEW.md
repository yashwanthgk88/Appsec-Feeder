# AppSec Feeder — Consolidated Overview

An internal intelligence platform that keeps an AppSec team current on three fronts,
with analyst-grade depth instead of headlines:

1. **Breach Deep-Dives** — root cause, attack chain, technical & business impact,
   detection guidance, remediation mapped to the SSDLC, practitioner POV.
2. **Tool Radar** — new/rising AppSec tools with honest pros/cons, comparison
   tables vs incumbents, and an adopt/pilot/watch/avoid verdict.
3. **AI × AppSec Watch** — signal-vs-hype analysis of AI-security developments,
   program impact, next-quarter actions.

Plus a **Point of View (POV)** engine writing in the voice of an EY AppSec
consulting practice: Business Impact Assessment (Board/CISO/CFO framing),
sector implications (banking / insurance / manufacturing), a three-horizon
remediation roadmap where every problem raised is paired with a fix, engagement
plays, and client conversation starters.

---

## What's in this bundle

```
poc/appsec-feeder.jsx      The original interactive POC (React artifact).
                           Live web-research per click via the Anthropic API.
                           Use for demos and UX iteration.

prod/                      The deployable product (lift-and-shift).
  docker-compose.yml       One command: docker compose up -d
  backend/                 FastAPI API + pipeline + in-container scheduler
    app.html               Analyst app  → served at  /
    admin.html             Admin console → served at /admin
  teams/                   Teams tab manifest + notification guide
  deploy/.env.example      All configuration (secrets are env-only)
  README.md                Architecture + cost table + governance checklist

docs/OVERVIEW.md           This document.
```

## POC vs Production — the key difference

| | POC (poc/) | Production (prod/) |
|---|---|---|
| Generation | Live per click, per user | Pipeline once daily → cached for everyone |
| Research | LLM web-search tool | Free feeds (CISA KEV, NVD, RSS) fetched by Python; LLM only analyzes fetched text |
| Cost scales with | Users × clicks | Content per day (~15 LLM calls/day) |
| LLM | Claude (fixed) | Any: Gemini/Groq/DeepSeek/OpenRouter/Ollama/Claude — switchable in admin panel; optional better model for POVs only |
| Auditability | Model's own searches | Every briefing traces to ingested source URLs |

## Production architecture (one paragraph)
A scheduler container runs the pipeline daily: ingest free sources → one LLM call
ranks each feed's top 10 → pre-generate deep-dives (top 3) and POV (top 1) →
store in SQLite on a Docker volume → push an Adaptive Card to Teams and
(optionally, after InfoSec/DPO sign-off) a WhatsApp template message. The API
container serves the cached briefings, the analyst app at `/`, and the admin
console at `/admin`. On-demand research for custom topics is the only per-use
cost and is rate-limited server-side.

## Admin console (`/admin`, separate ADMIN_TOKEN)
- **LLM Engine** — switch provider/model/endpoint live; POV-only model override
  (hybrid: free model for volume, better model for the partner-facing POV); test button.
- **Prompts** — every template editable with placeholders; reset-to-default.
- **Cost Dials** — top-N, dives/day, POVs/day, on-demand limit, source-char cap.
- **Notifications** — Teams webhook/header/items, WhatsApp recipients/template,
  disclaimer, digest feeds; send-test buttons.
- **Sources** — RSS lists per feed, editable at runtime (no redeploy).
- **Operations** — run pipeline now.
- Security posture: API keys and WhatsApp token are environment-only; the panel
  never sees secrets; Teams webhook masked on read; two separate tokens.

## Deploy (10 minutes)
```bash
cd prod
cp deploy/.env.example .env     # Gemini key (free tier works), 2 random tokens
docker compose up -d
# open http://localhost:8000/admin → unlock → Operations → RUN PIPELINE NOW
# open http://localhost:8000/    → the day's briefings
```

## Cost summary (defaults: ~15 LLM calls/day)
Gemini Flash free tier ≈ Rs 0 (policy-check data-training caveat) ·
Gemini paid ≈ Rs 100-300/mo · Claude Haiku ≈ Rs 500-900/mo ·
Hybrid (Gemini + Haiku POVs) ≈ Rs 150/mo · Ollama self-host ≈ Rs 0 tokens.
Verify current pricing; it changes often.

## Before go-live (governance)
1. InfoSec/DPO sign-off for WhatsApp (ships disabled) — intel transits Meta infra.
2. Personal API keys for a team tool may need procurement clearance regardless of vendor.
3. Replace shared-token auth with EY SSO / Azure AD before wide rollout.
4. Keep the "AI-generated — verify before client use" disclaimer everywhere.

## Roadmap candidates
Word/QBR export of briefings · weekly digest mode · Postgres option ·
Teams bot commands ("@Feeder pov on <topic>") · per-client source packs ·
SSO integration · usage analytics per feed.
