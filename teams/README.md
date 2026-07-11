# Teams integration — two pieces

## 1. Use the app inside Teams (static tab)
1. Deploy the web app over HTTPS (Teams requires TLS) and put its domain in
   `manifest.json` (`contentUrl`, `websiteUrl`, `validDomains`).
2. Generate a GUID for `id` (e.g. `uuidgen`), add 192x192 `color.png` and
   32x32 `outline.png` icons, zip the three files.
3. Teams → Apps → Manage your apps → "Upload an app" (or submit via the EY
   Teams admin catalog — for org-wide rollout the tenant admin publishes it).
4. Optional polish: add the Teams JS SDK (`@microsoft/teams-js`) in the
   frontend and call `app.initialize()` when `?inTeams=true` so theming and
   SSO can follow later.

## 2. Daily notifications into a channel (no bot needed)
Teams channel → ⋯ → Workflows → "Post to a channel when a webhook request is
received" → copy the URL → set `TEAMS_WEBHOOK_URL` in `.env`.
The pipeline posts an Adaptive Card each morning with the top 3 per feed and
an "Open AppSec Radar" button.

Upgrade path when you outgrow this: a proper Bot Framework bot enables
@mentions ("@Feeder pov on <topic>") and per-user DMs — bigger lift (Azure
Bot registration), not needed for v1.
