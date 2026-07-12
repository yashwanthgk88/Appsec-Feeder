"""FastAPI app serving cached briefings + rate-limited on-demand research.

In prod put this behind EY SSO / Azure AD; the shared token here is POC-grade.
"""
import datetime
import os
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import store
import analyze
import ingest
import enrich

app = FastAPI(title="AppSec Radar API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

APP_TZ = ZoneInfo(os.getenv("APP_TZ", "Asia/Kolkata"))  # all app timestamps in IST
# Gemini free-tier daily quota resets at Pacific midnight (DST-aware via zoneinfo).
QUOTA_TZ = ZoneInfo(os.getenv("QUOTA_TZ", "America/Los_Angeles"))

def _today() -> str:
    return datetime.datetime.now(APP_TZ).date().isoformat()

def _quota_day() -> str:
    return datetime.datetime.now(QUOTA_TZ).date().isoformat()

def _next_quota_reset() -> datetime.datetime:
    now = datetime.datetime.now(QUOTA_TZ)
    return (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def auth(token: str | None):
    if token != config.API_TOKEN:
        raise HTTPException(401, "Invalid token")


@app.get("/api/feeds/{feed}/index")
def feed_index(feed: str, x_api_token: str | None = Header(None)):
    auth(x_api_token)
    data = store.get_index(feed)
    if not data:
        raise HTTPException(404, "Index not generated yet — run the pipeline")
    enrich.enrich_items(data.get("items", []))  # EPSS + KEV, live at read time
    return data


@app.get("/api/feeds/{feed}/wire")
def feed_wire(feed: str, x_api_token: str | None = Header(None)):
    """Live wire — latest raw headlines for the feed (no AI, cached ~5 min)."""
    auth(x_api_token)
    if feed not in ("breach", "tools", "ai"):
        raise HTTPException(404, "Unknown feed")
    data = ingest.wire(feed)
    enrich.enrich_items(data.get("items", []))
    return data


@app.get("/api/exploited")
def exploited(x_api_token: str | None = Header(None)):
    """Actively-exploited CVEs (CISA KEV) ranked by EPSS — always populated."""
    auth(x_api_token)
    return {"items": enrich.exploited_watch(8)}


@app.get("/api/briefings/{bid}")
def briefing(bid: int, x_api_token: str | None = Header(None)):
    auth(x_api_token)
    b = store.get_briefing(bid)
    if not b:
        raise HTTPException(404, "Not found")
    return b


class ResearchRequest(BaseModel):
    feed: str
    topic: str
    kind: str = "dive"  # or "pov"


@app.post("/api/research")
def research(req: ResearchRequest, x_api_token: str | None = Header(None)):
    """On-demand generation for custom topics — the only per-use LLM cost."""
    auth(x_api_token)
    cached = store.find_briefing(req.feed, req.kind, req.topic)
    if cached:
        return {"id": cached["id"], "cached": True, "content_md": cached["content_md"]}
    today = _quota_day()
    if store.bump_ondemand(today) > config.ONDEMAND_DAILY_LIMIT:
        store.dec_ondemand(today)  # don't count the blocked attempt
        raise HTTPException(429, "Daily research budget reached — cached briefings remain available. "
                                 "See the budget indicator for when it resets.")
    # For custom topics we have no pre-fetched sources; use recent ingest as context
    raw = ingest.ingest(req.feed)
    context = "\n".join(f"- {i['title']} | {i['summary']} | {i['url']}" for i in raw[:40])
    fn = analyze.pov if req.kind == "pov" else analyze.deep_dive
    try:
        content = fn(req.feed, req.topic, context)
    except Exception as exc:  # degrade gracefully instead of a raw 500
        store.dec_ondemand(today)  # refund the budget slot on failure
        msg = str(exc)
        if getattr(exc, "status_code", None) == 429 or "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            raise HTTPException(429, "AI quota reached for today — cached briefings still work. "
                                     "New generation resumes after the provider quota resets, or enable billing.")
        raise HTTPException(502, f"AI generation failed ({type(exc).__name__}). Please retry shortly.")
    bid = store.save_briefing(req.feed, req.kind, req.topic, content)
    return {"id": bid, "cached": False, "content_md": content}


@app.get("/api/usage")
def usage(x_api_token: str | None = Header(None)):
    """Shared on-demand research budget + when the daily AI quota refreshes."""
    auth(x_api_token)
    reset = _next_quota_reset()
    left = int((reset - datetime.datetime.now(QUOTA_TZ)).total_seconds())
    return {"used": store.get_ondemand(_quota_day()), "limit": config.ONDEMAND_DAILY_LIMIT,
            "resets_at": reset.isoformat(), "resets_in_seconds": max(0, left)}


# ======================= ADMIN =======================
import os
from fastapi.responses import HTMLResponse
import settings as S
from notify import teams as teams_notify, whatsapp as wa_notify, email_notify

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-admin")

def admin_auth(token: str | None):
    if token != ADMIN_TOKEN:
        raise HTTPException(401, "Invalid admin token")

def _mask(url: str) -> str:
    return (url[:38] + "…") if url and len(url) > 40 else url

@app.get("/api/admin/config")
def admin_get_config(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    n = S.get_notifications()
    return {
        "llm": S.get_llm(),
        "dials": S.get_dials(),
        "notifications": {**n, "teams_webhook_url_masked": _mask(n.get("teams_webhook_url", ""))},
        "sources": __import__("ingest").rss_sources(),
        "prompts": {k: S.get_prompt(k) for k in S.DEFAULT_PROMPTS},
        "prompt_names": list(S.DEFAULT_PROMPTS),
        "note": "API keys are env-only by design and never exposed or editable here.",
    }

class ConfigPatch(BaseModel):
    llm: dict | None = None
    dials: dict | None = None
    notifications: dict | None = None
    sources: dict | None = None

@app.put("/api/admin/config")
def admin_put_config(patch: ConfigPatch, x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    if patch.llm is not None:
        S.put("llm", {**S.get_llm(), **patch.llm})
    if patch.dials is not None:
        S.put("dials", {**S.get_dials(), **{k: int(v) for k, v in patch.dials.items()}})
    if patch.notifications is not None:
        S.put("notifications", {**S.get_notifications(), **patch.notifications})
    if patch.sources is not None:
        S.put("sources", patch.sources)
    return {"ok": True}

class PromptBody(BaseModel):
    text: str

@app.put("/api/admin/prompts/{name}")
def admin_put_prompt(name: str, body: PromptBody, x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    try:
        S.set_prompt(name, body.text)
    except KeyError:
        raise HTTPException(404, "Unknown prompt")
    return {"ok": True}

@app.post("/api/admin/prompts/{name}/reset")
def admin_reset_prompt(name: str, x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    S.reset_prompt(name)
    return {"ok": True, "text": S.get_prompt(name)}

@app.post("/api/admin/test/llm")
def admin_test_llm(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    try:
        return {"ok": True, "reply": analyze.test_llm()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

@app.post("/api/admin/test/teams")
def admin_test_teams(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    teams_notify.send_daily_card({"breach": [{"title": "Test notification", "severity": "NOTABLE",
                                              "one_liner": "AppSec Radar Teams webhook is working."}]})
    return {"ok": True}

@app.post("/api/admin/test/whatsapp")
def admin_test_whatsapp(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    wa_notify.send_daily_digest({"breach": [{"title": "Test notification"}],
                                 "tools": [{"title": "-"}], "ai": [{"title": "-"}]})
    return {"ok": True}

@app.post("/api/admin/test/email")
def admin_test_email(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    sample = {
        "breach": [{"title": "Test breach headline", "severity": "CRITICAL",
                    "one_liner": "This is a test email from AppSec Radar."}],
        "tools": [{"title": "Test tool", "severity": "ADOPT", "one_liner": "Radar email delivery works."}],
        "ai": [{"title": "Test AI signal", "severity": "SIGNAL", "one_liner": "You can safely ignore this."}],
    }
    try:
        return email_notify.send_daily_digest(sample) or {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

_pipeline_state = {"running": False, "started_at": None, "finished_at": None, "error": None}


def _run_pipeline_bg():
    import pipeline
    _pipeline_state.update(running=True,
                           started_at=datetime.datetime.now(APP_TZ).isoformat(),
                           finished_at=None, error=None)
    try:
        pipeline.run()
    except Exception as exc:  # surface failures via the status endpoint
        _pipeline_state["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        _pipeline_state.update(running=False,
                               finished_at=datetime.datetime.now(APP_TZ).isoformat())


@app.post("/api/admin/run-pipeline")
def admin_run_pipeline(x_admin_token: str | None = Header(None)):
    """Manual trigger — runs in a background thread so the request returns
    immediately (the full run exceeds the 300s proxy timeout)."""
    admin_auth(x_admin_token)
    if _pipeline_state["running"]:
        return {"ok": True, "status": "already_running", "started_at": _pipeline_state["started_at"]}
    import threading
    threading.Thread(target=_run_pipeline_bg, daemon=True).start()
    return {"ok": True, "status": "started"}


@app.get("/api/admin/pipeline-status")
def admin_pipeline_status(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    return _pipeline_state

@app.get("/healthz")
def healthz():
    return {"ok": True}

_NOCACHE = {"Cache-Control": "no-cache, must-revalidate"}

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    path = os.path.join(os.path.dirname(__file__), "admin.html")
    return HTMLResponse(open(path).read(), headers=_NOCACHE)

@app.get("/", response_class=HTMLResponse)
def analyst_app():
    path = os.path.join(os.path.dirname(__file__), "app.html")
    return HTMLResponse(open(path).read(), headers=_NOCACHE)
