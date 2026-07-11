"""FastAPI app serving cached briefings + rate-limited on-demand research.

In prod put this behind EY SSO / Azure AD; the shared token here is POC-grade.
"""
import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import store
import analyze
import ingest

app = FastAPI(title="AppSec Feeder API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def auth(token: str | None):
    if token != config.API_TOKEN:
        raise HTTPException(401, "Invalid token")


@app.get("/api/feeds/{feed}/index")
def feed_index(feed: str, x_api_token: str | None = Header(None)):
    auth(x_api_token)
    data = store.get_index(feed)
    if not data:
        raise HTTPException(404, "Index not generated yet — run the pipeline")
    return data


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
    today = datetime.date.today().isoformat()
    if store.bump_ondemand(today) > config.ONDEMAND_DAILY_LIMIT:
        raise HTTPException(429, "Daily on-demand research limit reached — cached briefings remain available")
    # For custom topics we have no pre-fetched sources; use recent ingest as context
    raw = ingest.ingest(req.feed)
    context = "\n".join(f"- {i['title']} | {i['summary']} | {i['url']}" for i in raw[:40])
    fn = analyze.pov if req.kind == "pov" else analyze.deep_dive
    content = fn(req.feed, req.topic, context)
    bid = store.save_briefing(req.feed, req.kind, req.topic, content)
    return {"id": bid, "cached": False, "content_md": content}


# ======================= ADMIN =======================
import os
from fastapi.responses import HTMLResponse
import settings as S
from notify import teams as teams_notify, whatsapp as wa_notify

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
                                              "one_liner": "AppSec Feeder Teams webhook is working."}]})
    return {"ok": True}

@app.post("/api/admin/test/whatsapp")
def admin_test_whatsapp(x_admin_token: str | None = Header(None)):
    admin_auth(x_admin_token)
    wa_notify.send_daily_digest({"breach": [{"title": "Test notification"}],
                                 "tools": [{"title": "-"}], "ai": [{"title": "-"}]})
    return {"ok": True}

@app.post("/api/admin/run-pipeline")
def admin_run_pipeline(x_admin_token: str | None = Header(None)):
    """Manual trigger — runs synchronously; fine for admin use."""
    admin_auth(x_admin_token)
    import pipeline
    pipeline.run()
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/admin", response_class=HTMLResponse)
def admin_panel():
    path = os.path.join(os.path.dirname(__file__), "admin.html")
    return HTMLResponse(open(path).read())

@app.get("/", response_class=HTMLResponse)
def analyst_app():
    path = os.path.join(os.path.dirname(__file__), "app.html")
    return HTMLResponse(open(path).read())
