"""LLM layer — provider, models and prompts all resolved at runtime from settings."""
import json
import re
import time
import settings as S

# Free-tier LLM endpoints enforce per-minute request caps; a daily pipeline run
# bursts ~15 calls and will trip them. Retry on 429, honouring the server's
# suggested retryDelay when present, with a capped exponential fallback.
_MAX_RETRIES = 5


def _retry_delay_from(exc, attempt: int) -> float:
    m = re.search(r"retry in ([0-9.]+)s|retryDelay['\"]?:\s*['\"]?([0-9.]+)s", str(exc))
    if m:
        return min(60.0, float(m.group(1) or m.group(2)) + 1.0)
    return min(60.0, 2.0 ** attempt)


def _with_retries(call):
    for attempt in range(_MAX_RETRIES):
        try:
            return call()
        except Exception as exc:
            s = str(exc)
            is_429 = getattr(exc, "status_code", None) == 429 or "429" in s or "RESOURCE_EXHAUSTED" in s
            if not is_429:
                raise
            # A per-DAY quota cap won't recover within this request — fail fast
            # instead of burning ~5 min of backoff. Only per-minute limits retry.
            if "PerDay" in s or "GenerateRequestsPerDay" in s:
                print("[analyze] daily quota exhausted — failing fast")
                raise
            if attempt == _MAX_RETRIES - 1:
                raise
            delay = _retry_delay_from(exc, attempt)
            print(f"[analyze] 429 rate-limited; retry {attempt + 1}/{_MAX_RETRIES} in {delay:.0f}s")
            time.sleep(delay)


def _complete_with(provider: str, base_url: str, model: str, prompt: str, max_tokens: int) -> str:
    if provider == "anthropic":
        import config
        from anthropic import Anthropic
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = _with_retries(lambda: client.messages.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]))
        return "".join(b.text for b in msg.content if b.type == "text")
    import config
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=config.OPENAI_COMPAT_KEY or "ollama")
    # Gemini 3.x "thinking" models spend a large, hidden slice of the token
    # budget on reasoning; without capping it the visible completion gets
    # truncated (finish_reason=length) and JSON parsing fails. reasoning_effort
    # is forwarded via extra_body so non-reasoning backends simply ignore it.
    kwargs = {}
    if provider == "openai_compatible":
        kwargs["extra_body"] = {"reasoning_effort": "high"}
    resp = _with_retries(lambda: client.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}], **kwargs))
    return resp.choices[0].message.content or ""

def complete(prompt: str, max_tokens: int = 3000, task: str = "default") -> str:
    llm = S.get_llm()
    provider, model = llm["provider"], llm["model"]
    if provider == "anthropic":
        model = llm["anthropic_model"]
    # optional dedicated (higher-quality) model just for POVs
    if task == "pov" and llm.get("pov_provider"):
        provider = llm["pov_provider"]
        model = llm.get("pov_model") or model
    return _complete_with(provider, llm["base_url"], model, prompt, max_tokens)

def test_llm() -> str:
    return complete("Reply with exactly: OK", max_tokens=10)

def rank_index(feed_key: str, raw_items: list[dict]) -> list[dict]:
    dials = S.get_dials()
    corpus = "\n".join(
        f"- [{i}] {it['title']} | {it['source']} | {it['published']} | {it['summary'][:200]} | {it['url']}"
        for i, it in enumerate(raw_items[:60]))
    prompt = S.render(S.get_prompt("rank"), feed_context=S.FEED_CONTEXT[feed_key],
                      corpus=corpus, top_n=dials["top_n_index"],
                      severity_hint=S.SEVERITY_HINT[feed_key])
    text = complete(prompt, max_tokens=8000)
    clean = text.replace("```json", "").replace("```", "").strip()
    slice_ = clean[clean.find("["):clean.rfind("]") + 1]
    if not slice_:
        raise ValueError(f"rank_index: model returned no JSON array for feed '{feed_key}': {text[:200]!r}")
    ranked = json.loads(slice_)
    for r in ranked:
        r["source_urls"] = [raw_items[i]["url"] for i in r.get("source_indices", [])
                            if isinstance(i, int) and i < len(raw_items)][:4]
    return ranked[:dials["top_n_index"]]

def deep_dive(feed_key: str, topic: str, source_text: str) -> str:
    cap = S.get_dials()["max_source_chars"]
    prompt = S.render(S.get_prompt(f"dive_{feed_key}"), topic=topic, source=source_text[:cap])
    return complete(prompt, max_tokens=8000)

def pov(feed_key: str, topic: str, source_text: str) -> str:
    cap = S.get_dials()["max_source_chars"]
    prompt = S.render(S.get_prompt("pov"), topic=topic, source=source_text[:cap],
                      angle=S.POV_ANGLE[feed_key])
    return complete(prompt, max_tokens=8000, task="pov")
