"""Central config. Everything comes from environment / .env."""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM provider ---
# "openai_compatible" covers Google Gemini, Groq, DeepSeek, OpenRouter, Ollama
# (they all expose OpenAI-compatible endpoints) — set BASE_URL + KEY + MODEL.
# "anthropic" uses Claude Haiku directly.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai_compatible")

OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
OPENAI_COMPAT_KEY = os.getenv("OPENAI_COMPAT_KEY", "")
OPENAI_COMPAT_MODEL = os.getenv("OPENAI_COMPAT_MODEL", "gemini-2.5-flash")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

# --- Pipeline knobs (the cost dials) ---
TOP_N_INDEX = int(os.getenv("TOP_N_INDEX", "10"))       # items per feed index
DEEP_DIVES_PER_FEED = int(os.getenv("DEEP_DIVES_PER_FEED", "3"))
POVS_PER_FEED = int(os.getenv("POVS_PER_FEED", "1"))
MAX_SOURCE_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "24000"))  # ingested text cap per briefing

DB_PATH = os.getenv("DB_PATH", "briefings.db")

# --- API ---
API_TOKEN = os.getenv("API_TOKEN", "change-me")          # replace with EY SSO in prod
ONDEMAND_DAILY_LIMIT = int(os.getenv("ONDEMAND_DAILY_LIMIT", "20"))
APP_BASE_URL = os.getenv("APP_BASE_URL", "https://appsec-feeder.example.ey.com")

# --- Notifications ---
TEAMS_WEBHOOK_URL = os.getenv("TEAMS_WEBHOOK_URL", "")   # Teams Workflows incoming webhook
WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")         # Meta permanent token
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_RECIPIENTS = [r.strip() for r in os.getenv("WHATSAPP_RECIPIENTS", "").split(",") if r.strip()]
WHATSAPP_TEMPLATE = os.getenv("WHATSAPP_TEMPLATE", "appsec_daily_digest")

# --- Email (SMTP) digest ---
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")                   # mailbox / app-password user
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")           # app password (env-only, never in DB)
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
EMAIL_FROM = os.getenv("EMAIL_FROM", "") or SMTP_USER    # From address (defaults to SMTP_USER)
EMAIL_RECIPIENTS = [r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()]
EMAIL_SUBJECT = os.getenv("EMAIL_SUBJECT", "🛡️ AppSec Radar — Daily Intelligence")
