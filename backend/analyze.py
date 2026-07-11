"""LLM layer — provider, models and prompts all resolved at runtime from settings."""
import json
import settings as S

def _complete_with(provider: str, base_url: str, model: str, prompt: str, max_tokens: int) -> str:
    if provider == "anthropic":
        import config
        from anthropic import Anthropic
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        msg = client.messages.create(model=model, max_tokens=max_tokens,
                                     messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in msg.content if b.type == "text")
    import config
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=config.OPENAI_COMPAT_KEY or "ollama")
    resp = client.chat.completions.create(model=model, max_tokens=max_tokens,
                                          messages=[{"role": "user", "content": prompt}])
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
    text = complete(prompt, max_tokens=2000)
    clean = text.replace("```json", "").replace("```", "").strip()
    ranked = json.loads(clean[clean.find("["):clean.rfind("]") + 1])
    for r in ranked:
        r["source_urls"] = [raw_items[i]["url"] for i in r.get("source_indices", [])
                            if isinstance(i, int) and i < len(raw_items)][:4]
    return ranked[:dials["top_n_index"]]

def deep_dive(feed_key: str, topic: str, source_text: str) -> str:
    cap = S.get_dials()["max_source_chars"]
    prompt = S.render(S.get_prompt(f"dive_{feed_key}"), topic=topic, source=source_text[:cap])
    return complete(prompt, max_tokens=3500)

def pov(feed_key: str, topic: str, source_text: str) -> str:
    cap = S.get_dials()["max_source_chars"]
    prompt = S.render(S.get_prompt("pov"), topic=topic, source=source_text[:cap],
                      angle=S.POV_ANGLE[feed_key])
    return complete(prompt, max_tokens=3500, task="pov")
