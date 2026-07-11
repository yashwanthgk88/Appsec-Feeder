// Drop-in client for the React app: replaces direct Anthropic calls.
// The app becomes a thin client over the cached backend.

const API_BASE = "https://appsec-feeder.example.ey.com"; // your deployment
const TOKEN = "change-me"; // POC only — replace with EY SSO/AAD in prod

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", "x-api-token": TOKEN, ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

// Replaces loadIndex(): instant — the index is pre-generated daily.
export const getIndex = (feed) => api(`/api/feeds/${feed}/index`);

// Replaces generate() for items on the index that already carry dive_id/pov_id.
export const getBriefing = (id) => api(`/api/briefings/${id}`);

// Replaces generate() for custom topics — the only per-use LLM call, rate-limited server-side.
export const research = (feed, topic, kind = "dive") =>
  api(`/api/research`, { method: "POST", body: JSON.stringify({ feed, topic, kind }) });

/* Wiring into the existing appsec-feeder.jsx:
   1. Delete callClaude() and the index prompts from the frontend.
   2. loadIndex(feedKey)  -> getIndex(feedKey)          (renders items as before)
   3. DEEP-DIVE/POV click -> item.dive_id / item.pov_id ? getBriefing(id)
                                                        : research(feed, topic, kind)
   4. Follow-up questions -> research(feed, `${topic} — follow-up: ${question}`, kind)
      (server caches those too, so repeated questions cost nothing)             */
