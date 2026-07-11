# AppSec Feeder — Production Architecture

Generate-once / serve-many intelligence pipeline. Cost scales with **content generated
per day**, not with the number of analysts reading it.

```
                 ┌──────────────────────────────────────────────────────────┐
                 │  DAILY PIPELINE (cron, ~07:00 IST)                       │
                 │                                                          │
  FREE FEEDS ──▶ │  ingest.py      analyze.py         store                 │
  CISA KEV       │  fetch RSS/API ─▶ LLM ranks top10 ─▶ SQLite briefings.db │
  NVD CVEs       │                   LLM deep-dives                         │
  HackerNews,    │                   LLM POVs (top 3)                       │
  BleepingComp,  │                        │                                 │
  vendor blogs   │                        ▼                                 │
                 │              notify/teams.py  ──▶ Teams channel card     │
                 │              notify/whatsapp.py ─▶ WhatsApp template msg │
                 └──────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                 ┌──────────────────────────────────────────────────────────┐
                 │  api.py (FastAPI) — serves cached briefings              │
                 │  GET /api/feeds/{feed}/index                             │
                 │  GET /api/briefings/{id}                                 │
                 │  POST /api/research   (on-demand, rate-limited)          │
                 └──────────────────────────────────────────────────────────┘
                                          │
                          ┌───────────────┴───────────────┐
                          ▼                               ▼
                  React frontend                 Teams static tab
                  (thin client)                  (same URL, in-Teams)
```

## Why this is cheap
- Ingestion is plain Python + free public feeds (CISA KEV, NVD, RSS). Zero AI cost.
- The LLM never "searches the web" — it only analyzes text you already fetched.
  No web-search tool fees, far fewer tokens.
- Everything is generated once per day and cached. 15 analysts = same cost as 1.
- On-demand research is the only per-use cost, and it is rate-limited.

## LLM provider — one generic client, five options
`LLM_PROVIDER=openai_compatible` + a base URL covers Gemini, Groq, DeepSeek,
OpenRouter and self-hosted Ollama (all OpenAI-compatible). `anthropic` uses
Claude Haiku directly. Presets in `deploy/.env.example`.

Daily workload with default dials: ~15 LLM calls (3 rankings + 9 deep-dives
+ 3 POVs), roughly 150-250K tokens/day total. Approximate monthly cost:

| Option | Cost/month (approx) | Notes |
|--------|--------------------:|-------|
| Gemini Flash free tier | Rs 0 | Fits in free-tier rate limits; free tier may use data for training — inputs here are public feeds, but check firm policy |
| DeepSeek | Rs 50-150 | Cheapest paid; China-hosted — likely a firm-policy blocker |
| Gemini Flash paid | Rs 100-300 | Paid tier does not train on your data |
| Claude Haiku | Rs 500-900 | Best quality of the budget set, esp. for POVs |
| Ollama self-host | Rs 0 tokens | Your hardware, your uptime; weakest POV quality |

Verify current pricing/limits before committing — they change often.

## Components
| Path | Purpose |
|------|---------|
| `backend/ingest.py` | Fetch CISA KEV, NVD, and RSS sources per feed |
| `backend/analyze.py` | Provider-agnostic LLM client + ranking/deep-dive/POV prompts |
| `backend/pipeline.py` | Daily job: ingest → rank → generate → store → notify |
| `backend/api.py` | FastAPI serving cached briefings + rate-limited on-demand research |
| `backend/notify/teams.py` | Adaptive Card to a Teams channel via workflow webhook |
| `backend/notify/whatsapp.py` | WhatsApp Business Cloud API template push |
| `teams/manifest.json` | Teams app (static tab) wrapping the web UI |
| `frontend/api.js` | Drop-in client: replaces direct Anthropic calls in the React app |
| `deploy/` | Dockerfile, crontab, .env.example |

## Setup (15 minutes)
```bash
cd backend
pip install -r requirements.txt
cp ../deploy/.env.example .env    # fill in values
python pipeline.py                 # run one pipeline pass manually
uvicorn api:app --host 0.0.0.0 --port 8000
```
Then schedule: `crontab -e` → see `deploy/crontab.txt`.

## Governance checklist before go-live (you know this, but for the record)
- [ ] InfoSec/DPO sign-off on WhatsApp push — breach intel leaves the firm boundary
      to Meta's infrastructure. Teams-only is the safer default; WhatsApp is opt-in.
- [ ] Route LLM calls through firm-approved capacity (Azure OpenAI / EYQ) if mandated.
- [ ] Every briefing footer keeps the "AI-generated — verify before client use" label.
- [ ] Rate-limit + auth on `/api/research` (sample uses a shared token; put it behind
      EY SSO / Azure AD in prod).
