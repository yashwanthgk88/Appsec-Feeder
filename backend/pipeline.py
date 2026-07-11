"""Daily pipeline: ingest -> rank -> generate -> store -> notify.

Run manually: python pipeline.py
Schedule:     see deploy/crontab.txt
"""
import config
import settings as S
import ingest
import analyze
import store
from notify import teams, whatsapp

FEEDS = ["breach", "tools", "ai"]


def source_text_for(item: dict) -> str:
    parts = [item.get("one_liner", "")]
    for url in item.get("source_urls", []):
        parts.append(f"--- SOURCE: {url} ---")
        parts.append(ingest.fetch_article_text(url, S.get_dials()["max_source_chars"] // max(1, len(item.get('source_urls', [1])))))
    return "\n".join(parts)


def run():
    digest = {}
    for feed in FEEDS:
        print(f"[pipeline] {feed}: ingesting…")
        raw = ingest.ingest(feed)
        print(f"[pipeline] {feed}: {len(raw)} raw items, ranking…")
        top = analyze.rank_index(feed, raw)
        store.save_index(feed, top)
        digest[feed] = top

        # Pre-generate deep-dives for the top N, POVs for the very top
        dials = S.get_dials()
        for i, item in enumerate(top[: dials["deep_dives_per_feed"]]):
            topic = f"{item['title']} ({item.get('org','')}, {item.get('date','')})"
            if not store.find_briefing(feed, "dive", topic):
                print(f"[pipeline] {feed}: deep-dive {i+1} → {item['title']}")
                text = source_text_for(item)
                bid = store.save_briefing(feed, "dive", topic, analyze.deep_dive(feed, topic, text))
                item["dive_id"] = bid
            if i < dials["povs_per_feed"] and not store.find_briefing(feed, "pov", topic):
                print(f"[pipeline] {feed}: POV → {item['title']}")
                text = source_text_for(item)
                bid = store.save_briefing(feed, "pov", topic, analyze.pov(feed, topic, text))
                item["pov_id"] = bid
        store.save_index(feed, top)  # persist attached briefing ids

    # Notifications: headline = #1 breach; card carries the top 3 of each feed
    print("[pipeline] notifying…")
    teams.send_daily_card(digest)
    if config.WHATSAPP_ENABLED:
        whatsapp.send_daily_digest(digest)
    print("[pipeline] done.")


if __name__ == "__main__":
    run()
