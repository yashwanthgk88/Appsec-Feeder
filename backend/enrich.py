"""Exploitation-prediction enrichment — free, no API key, no LLM.

Attaches to feed items, purely from real sources:
  - exploited : CVE is on the CISA KEV list (actively exploited now)
  - epss      : FIRST.org EPSS probability (%) a CVE is exploited in the next 30 days
  - epss_pct  : EPSS percentile (0-100) vs all CVEs

EPSS is the standard data-driven exploitation signal; KEV is ground truth for
"exploited in the wild". Both are cached in-process so read-time enrichment is cheap.
"""
import re
import time
import requests

UA = {"User-Agent": "AppSecRadar/1.0 (internal intelligence tool)"}
EPSS_URL = "https://api.first.org/data/v1/epss"
KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.I)

_epss_cache: dict[str, tuple[float, dict | None]] = {}
_EPSS_TTL = 6 * 3600
_kev_cache: dict = {"ts": 0.0, "set": set()}
_KEV_TTL = 3600


def extract_cves(*texts) -> list[str]:
    out: list[str] = []
    for t in texts:
        for m in CVE_RE.findall(t or ""):
            u = m.upper()
            if u not in out:
                out.append(u)
    return out


def kev_set() -> set:
    now = time.time()
    if _kev_cache["set"] and now - _kev_cache["ts"] < _KEV_TTL:
        return _kev_cache["set"]
    try:
        data = requests.get(KEV_URL, headers=UA, timeout=30).json()
        s = {v["cveID"].upper() for v in data.get("vulnerabilities", [])}
        if s:
            _kev_cache.update(ts=now, set=s)
    except Exception as exc:
        print(f"[enrich] KEV fetch failed: {exc}")
    return _kev_cache["set"]


def epss_scores(cves: list[str]) -> dict:
    """{CVE: {"epss": prob0to1, "pct": percentile0to1}} — None value if unscored."""
    cves = [c.upper() for c in cves]
    now, out, need = time.time(), {}, []
    for c in cves:
        hit = _epss_cache.get(c)
        if hit and now - hit[0] < _EPSS_TTL:
            out[c] = hit[1]
        else:
            need.append(c)
    for i in range(0, len(need), 80):  # EPSS accepts batched, comma-separated CVEs
        chunk = need[i:i + 80]
        got = {}
        try:
            r = requests.get(EPSS_URL, params={"cve": ",".join(chunk)}, headers=UA, timeout=30).json()
            got = {d["cve"].upper(): {"epss": float(d["epss"]), "pct": float(d["percentile"])}
                   for d in r.get("data", [])}
        except Exception as exc:
            print(f"[enrich] EPSS fetch failed: {exc}")
        for c in chunk:
            _epss_cache[c] = (now, got.get(c))
            out[c] = got.get(c)
    return out


def exploited_watch(limit: int = 8) -> list[dict]:
    """Recent CISA KEV CVEs (actively exploited), ranked by EPSS. Always populated."""
    import ingest
    kev = ingest.fetch_cisa_kev(limit=30)
    cves = [extract_cves(k["title"])[0] for k in kev if extract_cves(k["title"])]
    scores = epss_scores(cves) if cves else {}
    out = []
    for k in kev:
        cs = extract_cves(k["title"])
        if not cs:
            continue
        cve = cs[0]
        s = scores.get(cve)
        name = k["title"].split(" — ", 1)[1] if " — " in k["title"] else k["title"]
        out.append({
            "cve": cve, "name": name, "url": k["url"], "added": k.get("published", ""),
            "epss": round(s["epss"] * 100, 1) if s else None,
            "epss_pct": round(s["pct"] * 100) if s else None,
        })
    out.sort(key=lambda x: (x["epss"] if x["epss"] is not None else -1), reverse=True)
    return out[:limit]


def enrich_items(items: list[dict]) -> None:
    """In place: attach exploited/cve/epss/epss_pct from each item's own text."""
    if not items:
        return
    kev = kev_set()
    all_cves: list[str] = []
    for it in items:
        c = extract_cves(it.get("title", ""), it.get("category", ""),
                         it.get("one_liner", ""), it.get("summary", ""))
        it["_cves"] = c
        all_cves.extend(c)
    scores = epss_scores(list(dict.fromkeys(all_cves))) if all_cves else {}
    for it in items:
        best, best_cve, exploited = None, None, False
        for c in it.pop("_cves", []):
            if c in kev:
                exploited = True
            s = scores.get(c)
            if s and (best is None or s["epss"] > best["epss"]):
                best, best_cve = s, c
        # never downgrade an existing exploited flag (e.g. wire KEV items)
        it["exploited"] = bool(it.get("exploited")) or exploited
        if best_cve:
            it["cve"] = best_cve
            it["epss"] = round(best["epss"] * 100, 1)
            it["epss_pct"] = round(best["pct"] * 100)
