"""Ingestion: fetch free public sources per feed. Zero AI cost.

Each function returns a list of dicts:
  {"title", "url", "published", "source", "summary"}
"""
import calendar
import time
import requests
import feedparser

UA = {"User-Agent": "AppSecFeeder/1.0 (internal intelligence tool)"}

# ---- Sources per feed ------------------------------------------------------
DEFAULT_RSS_SOURCES = {
    "breach": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/",
        "https://www.darkreading.com/rss.xml",
    ],
    # Tool Radar needs tool/product-focused sources, NOT general breach news —
    # AppSec vendor blogs (SAST/SCA/DAST/secrets) + a dedicated tools blog.
    "tools": [
        "https://snyk.io/blog/feed/",
        "https://semgrep.dev/blog/rss.xml",
        "https://blog.gitguardian.com/rss/",
        "https://portswigger.net/blog/rss",
        "https://www.darknet.org.uk/feed/",
        "https://www.helpnetsecurity.com/feed/",
    ],
    "ai": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://simonwillison.net/atom/everything/",
        "https://embracethered.com/blog/index.xml",
        "https://securityboulevard.com/feed/",
    ],
}

def rss_sources() -> dict:
    """Admin-editable at runtime; falls back to defaults per feed."""
    import settings as S
    return S.get("sources", DEFAULT_RSS_SOURCES)


CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
NVD_RECENT_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=40&noRejected"


def fetch_rss(feed_key: str, max_per_source: int = 15) -> list[dict]:
    items = []
    for url in rss_sources().get(feed_key, []):
        try:
            parsed = feedparser.parse(url)
            for e in parsed.entries[:max_per_source]:
                items.append({
                    "title": e.get("title", "").strip(),
                    "url": e.get("link", ""),
                    "published": e.get("published", e.get("updated", "")),
                    "source": parsed.feed.get("title", url),
                    "summary": (e.get("summary", "") or "")[:600],
                })
        except Exception as exc:  # a dead feed must never kill the pipeline
            print(f"[ingest] RSS failed {url}: {exc}")
        time.sleep(0.5)
    return items


def fetch_cisa_kev(limit: int = 20) -> list[dict]:
    """Known-exploited vulns — the strongest 'this breach class is real' signal."""
    try:
        data = requests.get(CISA_KEV_URL, headers=UA, timeout=30).json()
        vulns = sorted(data.get("vulnerabilities", []),
                       key=lambda v: v.get("dateAdded", ""), reverse=True)[:limit]
        return [{
            "title": f"{v['cveID']} — {v.get('vulnerabilityName','')} ({v.get('vendorProject','')})",
            "url": f"https://nvd.nist.gov/vuln/detail/{v['cveID']}",
            "published": v.get("dateAdded", ""),
            "source": "CISA KEV",
            "summary": v.get("shortDescription", "")[:600],
        } for v in vulns]
    except Exception as exc:
        print(f"[ingest] CISA KEV failed: {exc}")
        return []


def fetch_nvd_recent() -> list[dict]:
    try:
        data = requests.get(NVD_RECENT_URL, headers=UA, timeout=30).json()
        out = []
        for c in data.get("vulnerabilities", []):
            cve = c.get("cve", {})
            desc = next((d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"), "")
            out.append({
                "title": cve.get("id", ""),
                "url": f"https://nvd.nist.gov/vuln/detail/{cve.get('id','')}",
                "published": cve.get("published", ""),
                "source": "NVD",
                "summary": desc[:600],
            })
        return out
    except Exception as exc:
        print(f"[ingest] NVD failed: {exc}")
        return []


def fetch_article_text(url: str, max_chars: int) -> str:
    """Fetch full article body for deep-dives (naive text extraction, good enough)."""
    try:
        html = requests.get(url, headers=UA, timeout=30).text
        # strip tags crudely; swap in trafilatura/readability for prod polish
        import re
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", html)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception as exc:
        print(f"[ingest] article fetch failed {url}: {exc}")
        return ""


import urllib.parse

# Clean, consistent display names for the wire (feed titles are unreliable).
FRIENDLY_SOURCES = {
    "feeds.feedburner.com": "The Hacker News", "thehackernews.com": "The Hacker News",
    "bleepingcomputer.com": "BleepingComputer", "krebsonsecurity.com": "Krebs on Security",
    "darkreading.com": "Dark Reading", "helpnetsecurity.com": "Help Net Security",
    "securityboulevard.com": "Security Boulevard", "snyk.io": "Snyk", "semgrep.dev": "Semgrep",
    "gitguardian.com": "GitGuardian", "portswigger.net": "PortSwigger", "darknet.org.uk": "Darknet",
    "simonwillison.net": "Simon Willison", "embracethered.com": "Embrace The Red",
}


def _friendly(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    for dom, name in FRIENDLY_SOURCES.items():
        if host.endswith(dom):
            return name
    core = host.split(".")[0]
    return core[:1].upper() + core[1:] if core else url


def _entry_image(e) -> str:
    """Best-effort thumbnail from an RSS entry (media/enclosure). May be empty."""
    for key in ("media_thumbnail", "media_content"):
        v = e.get(key)
        if v and isinstance(v, list) and v[0].get("url"):
            return v[0]["url"]
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and str(l.get("type", "")).startswith("image"):
            return l.get("href", "")
    return ""


_wire_cache: dict[str, tuple[float, dict]] = {}
_WIRE_TTL = 300  # seconds — the wire refreshes a few times an hour, not per request


def wire(feed_key: str, limit: int = 12) -> dict:
    """Latest RAW headlines for a feed — no AI, real sources, newest first.

    Returns {generated_at, sources:[names], items:[{title,url,source,ts,exploited,image}]}.
    Cached per feed for _WIRE_TTL so page loads don't refetch every RSS source.
    """
    now = time.time()
    hit = _wire_cache.get(feed_key)
    if hit and now - hit[0] < _WIRE_TTL:
        return hit[1]

    items, sources = [], []
    for url in rss_sources().get(feed_key, []):
        try:
            parsed = feedparser.parse(url)
            sname = _friendly(url)
            sources.append(sname)
            for e in parsed.entries[:12]:
                pp = e.get("published_parsed") or e.get("updated_parsed")
                items.append({
                    "title": (e.get("title", "") or "").strip(),
                    "url": e.get("link", ""),
                    "source": sname,
                    "ts": calendar.timegm(pp) if pp else 0,
                    "exploited": False,
                    "image": _entry_image(e),
                })
        except Exception as exc:  # a dead feed must never break the wire
            print(f"[wire] RSS failed {url}: {exc}")
        time.sleep(0.2)

    # Breach wire folds in CISA KEV additions — the strongest "exploited now" signal.
    if feed_key == "breach":
        for v in fetch_cisa_kev(8):
            ts = 0
            try:
                ts = calendar.timegm(time.strptime(v["published"], "%Y-%m-%d"))
            except Exception:
                pass
            items.append({"title": v["title"], "url": v["url"], "source": "CISA KEV",
                          "ts": ts, "exploited": True, "image": ""})
        sources.append("CISA KEV")

    # Newest first, deduped, and capped per source so no single feed dominates.
    seen, per, out = set(), {}, []
    for it in sorted(items, key=lambda x: x["ts"], reverse=True):
        k = it["title"].lower()[:80]
        if not k or k in seen:
            continue
        if per.get(it["source"], 0) >= 4:
            continue
        seen.add(k)
        per[it["source"]] = per.get(it["source"], 0) + 1
        out.append(it)
        if len(out) >= limit:
            break
    data = {"generated_at": int(now), "sources": sorted(set(sources)), "items": out}
    _wire_cache[feed_key] = (now, data)
    return data


def ingest(feed_key: str) -> list[dict]:
    items = fetch_rss(feed_key)
    if feed_key == "breach":
        items = fetch_cisa_kev() + items + fetch_nvd_recent()
    # dedupe by title
    seen, out = set(), []
    for it in items:
        k = it["title"].lower()[:80]
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out
