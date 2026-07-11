"""Push the daily digest via the WhatsApp Business Cloud API (Meta).

Prerequisites (one-time):
  1. Meta Business account + WhatsApp Business API app, business verification.
  2. A phone number registered to the app (WHATSAPP_PHONE_NUMBER_ID).
  3. An APPROVED message template — business-initiated pushes MUST use a
     template outside the 24-hour customer-service window. Suggested template
     'appsec_daily_digest' with 3 body variables:
       "🛡️ AppSec Feeder daily: Top breach: {{1}}. Top tool: {{2}}.
        AI watch: {{3}}. Open the app for full briefings & POVs."
  4. Recipients must opt in (firm policy + Meta policy).

Governance note: this sends breach intel through Meta infrastructure —
get InfoSec/DPO sign-off before enabling (WHATSAPP_ENABLED=true).
Alternative with the same code shape: Twilio's WhatsApp API.
"""
import requests
import config
import settings as S

GRAPH_URL = "https://graph.facebook.com/v21.0/{pnid}/messages"


def _headline(items):
    return items[0]["title"][:120] if items else "no items today"


def send_daily_digest(digest: dict):
    n = S.get_notifications()
    recipients = n.get("whatsapp_recipients") or config.WHATSAPP_RECIPIENTS
    if not (n.get("whatsapp_enabled") and config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID and recipients):
        print("[whatsapp] disabled or not configured, skipping")
        return
    params = [_headline(digest.get("breach", [])),
              _headline(digest.get("tools", [])),
              _headline(digest.get("ai", []))]
    url = GRAPH_URL.format(pnid=config.WHATSAPP_PHONE_NUMBER_ID)
    headers = {"Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
               "Content-Type": "application/json"}
    for to in recipients:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": n.get("whatsapp_template") or config.WHATSAPP_TEMPLATE,
                "language": {"code": "en"},
                "components": [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }],
            },
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"[whatsapp] → {to}: {r.status_code} {r.text[:120]}")
