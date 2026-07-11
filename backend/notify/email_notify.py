"""Send the daily digest as an HTML email over SMTP.

Works with any SMTP relay (Gmail, Office 365, org relay). Credentials are
env-only. Gmail needs an App Password (not your normal password) with 2FA on:
  https://myaccount.google.com/apppasswords

Env: EMAIL_ENABLED, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
     SMTP_STARTTLS, EMAIL_FROM, EMAIL_RECIPIENTS, EMAIL_SUBJECT
"""
import smtplib
import ssl
from email.message import EmailMessage

import config
import settings as S

SEV_EMOJI = {"CRITICAL": "🔴", "HIGH": "🟠", "NOTABLE": "🟡",
             "ADOPT": "🟢", "PILOT": "🟡", "WATCH": "⚪",
             "SIGNAL": "🟢", "HYPE": "⚪"}
FEED_LABEL = {"breach": "Breach Deep-Dives", "tools": "Tool Radar", "ai": "AI × AppSec"}

INK, YELLOW, GRAY = "#141414", "#FFE600", "#5A5D58"


def _esc(t: str) -> str:
    return (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_html(digest: dict, n: dict) -> str:
    per_feed = n.get("teams_items_per_feed", 3)
    app_url = config.APP_BASE_URL
    sections = []
    for feed, items in digest.items():
        rows = []
        for it in items[:per_feed]:
            emoji = SEV_EMOJI.get(it.get("severity", ""), "•")
            rows.append(
                f'<tr><td style="padding:8px 0;border-top:1px solid #E7E8E2;vertical-align:top;font-size:14px">'
                f'{emoji} <b>{_esc(it.get("title",""))}</b>'
                f'<div style="color:{GRAY};font-size:13px;margin-top:2px">{_esc(it.get("one_liner",""))}</div></td></tr>')
        sections.append(
            f'<h2 style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;margin:22px 0 4px">'
            f'<span style="background:{INK};color:{YELLOW};padding:3px 8px">{_esc(FEED_LABEL.get(feed, feed))}</span></h2>'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{"".join(rows) or "<tr><td style=color:#5A5D58>No items today.</td></tr>"}</table>')
    disclaimer = _esc(n.get("disclaimer", "AI-generated from public sources — verify before client use."))
    return f"""<!doctype html><html><body style="margin:0;background:#F1F2EF;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:{INK}">
<div style="max-width:640px;margin:0 auto;background:#fff">
<div style="background:{INK};padding:18px 22px">
  <div style="color:{YELLOW};font-size:11px;letter-spacing:.2em;font-family:monospace">APPSEC TEAM // INTERNAL INTELLIGENCE</div>
  <div style="color:#fff;font-size:26px;font-weight:800">AppSec <span style="color:{YELLOW}">Radar</span></div>
</div>
<div style="padding:8px 22px 24px">
  {"".join(sections)}
  <div style="margin-top:26px">
    <a href="{app_url}" style="background:{YELLOW};color:{INK};text-decoration:none;font-weight:800;font-size:12px;letter-spacing:.06em;padding:11px 18px;display:inline-block">OPEN APPSEC RADAR ▸</a>
  </div>
  <p style="color:{GRAY};font-size:11px;margin-top:22px">{disclaimer}</p>
</div></div></body></html>"""


def _build_text(digest: dict, n: dict) -> str:
    per_feed = n.get("teams_items_per_feed", 3)
    lines = ["AppSec Radar — Daily Intelligence", ""]
    for feed, items in digest.items():
        lines.append(FEED_LABEL.get(feed, feed).upper())
        for it in items[:per_feed]:
            lines.append(f" - [{it.get('severity','')}] {it.get('title','')}: {it.get('one_liner','')}")
        lines.append("")
    lines.append(f"Open: {config.APP_BASE_URL}")
    lines.append(n.get("disclaimer", "AI-generated from public sources — verify before client use."))
    return "\n".join(lines)


def send_daily_digest(digest: dict):
    n = S.get_notifications()
    recipients = n.get("email_recipients") or config.EMAIL_RECIPIENTS
    if not (n.get("email_enabled") and config.SMTP_HOST and config.SMTP_USER
            and config.SMTP_PASSWORD and recipients):
        print("[email] disabled or not configured, skipping")
        return {"ok": False, "skipped": "disabled or not configured"}

    digest = {k: v for k, v in digest.items() if k in n.get("feeds_in_digest", list(digest))}
    msg = EmailMessage()
    msg["Subject"] = n.get("email_subject") or config.EMAIL_SUBJECT
    msg["From"] = config.EMAIL_FROM or config.SMTP_USER
    msg["To"] = ", ".join(recipients)
    msg.set_content(_build_text(digest, n))
    msg.add_alternative(_build_html(digest, n), subtype="html")

    if config.SMTP_STARTTLS:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    else:  # implicit TLS (port 465)
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT,
                              context=ssl.create_default_context(), timeout=30) as s:
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.send_message(msg)
    print(f"[email] sent to {len(recipients)} recipient(s)")
    return {"ok": True, "recipients": len(recipients)}
