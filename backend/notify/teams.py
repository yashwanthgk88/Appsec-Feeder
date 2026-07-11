"""Post the daily digest to a Teams channel as an Adaptive Card.

Setup (2 minutes, no bot registration needed):
  Teams channel → ⋯ → Workflows → "Post to a channel when a webhook request
  is received" → copy the URL into TEAMS_WEBHOOK_URL.
(Classic Office 365 connectors are retired; the Workflows webhook is the
current supported path and accepts the same Adaptive Card payload.)
"""
import requests
import config
import settings as S

SEV_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "NOTABLE": "🟡",
             "ADOPT": "🟢", "PILOT": "🟡", "WATCH": "⚪",
             "SIGNAL": "🟢", "HYPE": "⚪"}
FEED_LABEL = {"breach": "Breach Deep-Dives", "tools": "Tool Radar", "ai": "AI × AppSec"}


def send_daily_card(digest: dict):
    n = S.get_notifications()
    url = n.get("teams_webhook_url") or config.TEAMS_WEBHOOK_URL
    if not (n.get("teams_enabled") and url):
        print("[teams] disabled or no webhook, skipping")
        return
    digest = {k: v for k, v in digest.items() if k in n.get("feeds_in_digest", list(digest))}
    body = [{
        "type": "TextBlock", "size": "Large", "weight": "Bolder",
        "text": n.get("teams_header", "AppSec Radar — Daily Intelligence"),
    }]
    for feed, items in digest.items():
        body.append({"type": "TextBlock", "weight": "Bolder", "spacing": "Medium",
                     "text": FEED_LABEL.get(feed, feed)})
        for item in items[: n.get("teams_items_per_feed", 3)]:
            emoji = SEV_EMOJI.get(item.get("severity", ""), "•")
            body.append({"type": "TextBlock", "wrap": True,
                         "text": f"{emoji} **{item['title']}** — {item.get('one_liner','')}"})
    body.append({"type": "TextBlock", "spacing": "Medium", "isSubtle": True, "wrap": True,
                 "text": n.get("disclaimer", "AI-generated — verify before client use.")})

    card = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard", "version": "1.4", "body": body,
                "actions": [{"type": "Action.OpenUrl", "title": "Open AppSec Radar",
                             "url": config.APP_BASE_URL}],
            },
        }],
    }
    r = requests.post(url, json=card, timeout=30)
    print(f"[teams] posted, status {r.status_code}")
