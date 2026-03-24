# Venture Builder — Coding Standards

## Architecture
- Flask app, single file (app.py)
- SQLite for data (sqlite3 built-in)
- External integrations: import from ./integrations/ only
- Templates in templates/, static in static/

## Code Quality (mandatory)
- Every external API call wrapped in try/except with fallback
- Validate all required env vars at startup:
  required = ["POLAR_PRODUCT_ID", "APP_SECRET_KEY"]
  missing = [v for v in required if not os.environ.get(v)]
  if missing: raise RuntimeError(f"Missing env vars: {missing}")
- Log every request and error: app.logger.info() / app.logger.error()
- Return JSON errors, never HTML errors on API routes

## requirements.txt (mandatory)
Always include: flask, gunicorn, requests
Add others only if actually used in code.

## External Integrations
Pre-copied to ./integrations/ — import directly:
  from integrations.devto import post_article
  from integrations.hackernews import submit_post
  from integrations.indiehackers import generate_post_draft

## Routes (mandatory)
- GET /health → {"status": "ok"}
- GET / → index.html
- POST /submit → validate input, save to DB, return JSON
- GET /pay → redirect to Polar checkout

## Design (mandatory)
Before writing any HTML/CSS, choose ONE visual identity:
- Dark minimal: bg-gray-950, white text, indigo accents
- Bold colorful: bright hero, strong contrast, vivid CTA
- Professional clean: white bg, navy/slate text, clear hierarchy

Rules:
- Never use plain Tailwind defaults (bg-blue-500 button on white bg)
- H1 must be > 40px, bold, with clear value proposition
- CTA button: vivid color, py-3 px-8, above the fold
- Mobile-first: test at 375px width mentally before writing

## OAuth Integrations
If product needs user authentication with external service:
  from integrations.oauth.quickbooks import get_auth_url, get_tokens
  from integrations.oauth.hubspot import get_auth_url, get_tokens
  from integrations.oauth.shopify import get_auth_url, get_tokens

OAuth flow pattern:
  GET /connect → redirect to get_auth_url()
  GET /callback → exchange code with get_tokens() → save_tokens()
  GET /sync → load_tokens() → call API

## Background Jobs
For scheduled sync tasks:
  from integrations.scheduler import add_interval_job, start
  start scheduler in app startup, add jobs after OAuth connect

## Business Value Check
Before writing any feature ask:
"Would a small business owner pay $15/month for this specific feature?"
If not — simplify or remove it.
