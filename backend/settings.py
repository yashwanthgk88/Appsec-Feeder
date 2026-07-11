"""DB-backed runtime settings + editable prompt templates.

Precedence: admin-panel value (DB) > .env default.
Secrets (API keys) are ENV-ONLY by design — the admin panel never sees them.
Prompt templates use <<PLACEHOLDER>> tokens (safe against braces in prompt text).
"""
import json
import sqlite3
import config

def _db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value_json TEXT)")
    return conn

def get(key: str, default):
    with _db() as conn:
        row = conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default

def put(key: str, value):
    with _db() as conn:
        conn.execute("REPLACE INTO settings (key, value_json) VALUES (?,?)", (key, json.dumps(value)))

# ---------------- typed accessors with env defaults ----------------

def get_llm():
    return get("llm", {
        "provider": config.LLM_PROVIDER,                 # openai_compatible | anthropic
        "base_url": config.OPENAI_COMPAT_BASE_URL,
        "model": config.OPENAI_COMPAT_MODEL,
        "anthropic_model": config.ANTHROPIC_MODEL,
        "pov_provider": "",                              # optional override just for POVs
        "pov_model": "",
    })

def get_dials():
    return get("dials", {
        "top_n_index": config.TOP_N_INDEX,
        "deep_dives_per_feed": config.DEEP_DIVES_PER_FEED,
        "povs_per_feed": config.POVS_PER_FEED,
        "ondemand_daily_limit": config.ONDEMAND_DAILY_LIMIT,
        "max_source_chars": config.MAX_SOURCE_CHARS,
    })

def get_notifications():
    return get("notifications", {
        "teams_enabled": bool(config.TEAMS_WEBHOOK_URL),
        "teams_webhook_url": config.TEAMS_WEBHOOK_URL,
        "teams_items_per_feed": 3,
        "teams_header": "🛡️ AppSec Radar — Daily Intelligence",
        "whatsapp_enabled": config.WHATSAPP_ENABLED,
        "whatsapp_recipients": config.WHATSAPP_RECIPIENTS,
        "whatsapp_template": config.WHATSAPP_TEMPLATE,
        "disclaimer": "AI-generated from public sources — verify before client use.",
        "feeds_in_digest": ["breach", "tools", "ai"],
    })

# ---------------- prompt templates ----------------

FEED_CONTEXT = {
    "breach": "breaches and security incidents relevant to application security (exploited app vulns, supply chain, API abuse, leaked secrets, AI-related incidents)",
    "tools": "new or significantly updated application security tools (SAST, SCA, DAST, secrets, ASPM, supply chain, AI-powered AppSec)",
    "ai": "developments at the intersection of AI and application security (AI-generated code risk, agentic AppSec, LLM/agent/MCP security, regulation)",
}
SEVERITY_HINT = {"breach": "CRITICAL|HIGH|NOTABLE", "tools": "ADOPT|PILOT|WATCH", "ai": "SIGNAL|HYPE|WATCH"}
POV_ANGLE = {
    "breach": "Frame this breach as a case study in systemic failure, not an isolated event.",
    "tools": "Frame this tool within the AppSec market consolidation story and buyer economics.",
    "ai": "Frame this within the AI-vs-AppSec arms race and the gap between demo capability and enterprise adoption reality.",
}

DEFAULT_PROMPTS = {
    "rank": """You are an application security intelligence analyst. Below are recent items from monitored sources about <<FEED_CONTEXT>>.

<<CORPUS>>

Select and rank up to <<TOP_N>> items that genuinely match this feed's focus (<<FEED_CONTEXT>>), most significant first, for a senior AppSec consulting team. Merge duplicates covering the same story. CRITICAL: only include items that actually fit the focus — if an item does not fit (e.g. a breach story in a tools feed), EXCLUDE it. Return FEWER than <<TOP_N>> rather than padding the list with off-topic items. Respond with ONLY a raw JSON array, no fences:
[{"title":"short name","org":"who","date":"Mon YYYY","category":"short category","severity":"<<SEVERITY_HINT>>","one_liner":"why the team should care, max 25 words","source_indices":[ints of the corpus items this is based on]}]
Real items only; never invent. JSON only.""",

    "dive_breach": """You are a principal application security analyst writing an internal intelligence briefing for a senior AppSec consulting team (banking, insurance, manufacturing clients) on: "<<TOPIC>>".

SOURCE MATERIAL (base the briefing ONLY on this plus well-established security knowledge; if the material doesn't cover something, say so rather than guessing):
<<SOURCE>>

Write a detailed markdown report with EXACTLY these sections:
## Executive Summary
## Incident Overview
## Root Cause
## Technical Impact
## Business Impact
## How to Detect
## How to Fix & Prevent
## Practitioner POV
## Sources

Rules: technical and specific; honest about confirmed vs speculated; never invent CVEs, numbers or quotes; cite the source URLs used. Markdown only, no preamble.""",

    "dive_tools": """You are a principal application security analyst writing an internal tool-evaluation briefing for a senior AppSec consulting team on: "<<TOPIC>>".

SOURCE MATERIAL (base the briefing ONLY on this plus well-established security knowledge; if the material doesn't cover something, say so rather than guessing):
<<SOURCE>>

Write a detailed markdown report with EXACTLY these sections:
## Executive Summary
## What It Is
## Key Capabilities
## Pros
## Cons
## Comparison vs Incumbents (markdown table vs 2-3 established peers)
## Where It Fits
## Practitioner POV
## Sources

Rules: honest about marketing claims vs verified capability; never invent benchmarks or pricing. Markdown only, no preamble.""",

    "dive_ai": """You are a principal application security analyst writing an internal AI-security intelligence briefing for a senior AppSec consulting team on: "<<TOPIC>>".

SOURCE MATERIAL (base the briefing ONLY on this plus well-established security knowledge; if the material doesn't cover something, say so rather than guessing):
<<SOURCE>>

Write a detailed markdown report with EXACTLY these sections:
## Executive Summary
## What's New
## Why It Matters
## Threats & Opportunities
## Impact on AppSec Programs
## Practitioner POV
## Next Quarter Actions
## Sources

Rules: specific with names and dates; honest about uncertainty; never invent papers, products or quotes. Markdown only, no preamble.""",

    "pov": """You are writing as EY's Application Security consulting team — a Big Four practice delivering threat modeling, secure code review, SAST/SCA/DAST programs, DevSecOps transformation and SSDLC assessments for banking, insurance and manufacturing clients. Produce a detailed internal Point of View on: "<<TOPIC>>".

SOURCE MATERIAL (base every factual claim on this; label estimates as estimates):
<<SOURCE>>

Voice: trusted advisor to client executives — business-first, plain language a CFO can follow, technical depth where it earns its place. Every problem raised MUST be paired with a concrete fix. <<ANGLE>>

Write markdown with EXACTLY these sections:
## The Bottom Line
## Business Impact Assessment
(revenue/operational disruption; direct costs; regulatory exposure — GDPR, DPDP, SEC, DORA, sector regulators; brand; third-party fallout; then per stakeholder: Board / CISO / CFO)
## What Most Are Getting Wrong
## Sector Implications
(sub-sections: Banking & Financial Services, Insurance, Manufacturing)
## How to Fix It — Our Remediation Roadmap
(Immediate 0-30 days / Near-term 30-90 days mapped to SSDLC stages / Strategic 6-18 months; for each: what, why it works, how to verify)
## Our Position
(4-6 quotable numbered stances with one-line rationale, plus a 12-24 month outlook)
## How Our Team Helps
(engagement plays traced to fixes above: trigger, deliverable, outcome)
## Client Conversation Starters
## Sources

Rules: grounded, honest about uncertainty, never invent statistics/penalties/CVEs; opinionated but defensible. Markdown only, no preamble.""",
}

def get_prompt(name: str) -> str:
    overrides = get("prompts", {})
    return overrides.get(name) or DEFAULT_PROMPTS[name]

def set_prompt(name: str, text: str):
    if name not in DEFAULT_PROMPTS:
        raise KeyError(name)
    overrides = get("prompts", {})
    overrides[name] = text
    put("prompts", overrides)

def reset_prompt(name: str):
    overrides = get("prompts", {})
    overrides.pop(name, None)
    put("prompts", overrides)

def render(template: str, **tokens) -> str:
    out = template
    for k, v in tokens.items():
        out = out.replace(f"<<{k.upper()}>>", str(v))
    return out
