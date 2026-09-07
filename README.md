# LoopLearn — AI Daily Learning Pipeline

LoopLearn is a Flask backend that automatically researches, writes, and publishes one technical "daily article" per topic domain (System Design, Backend Engineering, Operating Systems, Cybersecurity, APIs, etc.), every day, with zero manual authoring. It picks an unwritten topic from a concept graph, searches the web for source material, scrapes and cleans it, sends it to Gemini to produce a structured engineering-focused article (with a Mermaid diagram, code artifact, flashcards, case study, anti-patterns...), generates a narrated audio version via TTS, and publishes it — free for everyone or gated behind a Razorpay subscription. It also serves the read APIs the frontend consumes, handles Google-OAuth login, per-workspace/team subscriptions, an inline "explain this term" AI tutor, and admin review tooling.

## How the pipeline works, end to end

1. **Topic selection** (`app/services/pick_topic.py`) — picks a random `domain` node from a concept graph (`concept_nodes` / `concept_edges` tables), then a connected `concept` node under it that hasn't already been published or turned into a candidate, avoiding anything used in the last 30 days (`topic_history`). `pick_topic_domain(domain)` does the same but scoped to one requested domain, with a "bootstrap" fallback to the domain node itself if all its concepts are exhausted.
2. **Source discovery** (`app/services/fetcher.py`) — searches DuckDuckGo (`ddgs`) for `"<topic> explained"` and returns up to 20 candidate URLs, which are stored in the `sources` table (`source_service.store_sources_bulk`) and linked to the topic (`topic_source_service`).
3. **Scraping** (`app/services/scraper.py`, `source_scrape_service.py`) — downloads and extracts main article text with `trafilatura`, discarding pages under 500 characters.
4. **Cleaning / structuring** (`text_cleaner.py`, `text_structurer.py`) — strips boilerplate (cookie banners, "table of contents", short lines) and can split scraped text into labeled sections for preview endpoints.
5. **AI compilation** (`app/services/topic_compiler.py`) — sends the topic plus scraped source text to **Gemini 2.5 Flash** (`google-genai`) with a strict system prompt, requesting a single JSON object containing: intro hook, "what is it" / "why it matters", a practical code/config/CLI/SQL artifact with line-by-line breakdown, theory + trade-offs, observability metrics, anti-patterns, a real-world case study, interview flashcards, a Mermaid diagram, and suggested child topics (used to grow the concept graph). Calls retry with exponential backoff (`tenacity`).
6. **Article rendering** (`pipeline_service.render_article_md`) — turns the compiled JSON into a Markdown article.
7. **Audio generation** (`app/services/audio_service.py`) — strips Markdown syntax, prepends a spoken intro ("Hello there, welcome to LoopLearn..."), synthesizes narration with **edge-tts** (word-level timestamps captured for karaoke-style highlighting), uploads the MP3 to **Cloudinary**, and deletes the local temp file.
8. **Candidate creation** (`app/models/article_candidate.py`) — the compiled article, diagram, audio URL and raw JSON are saved as a `pending` candidate.
9. **Child topics** — new topics/edges suggested by Gemini are inserted back into the concept graph so future runs have more to pick from.
10. **Publishing** — two paths:
    - **Manual/free pipeline** (`run_pipeline`, triggered by `POST /api/pipeline/run`): creates a candidate only; an admin later reviews and approves it via `POST /api/admin/candidates/approve/<id>`, which publishes it for a chosen date (default: tomorrow) and marks it `public` audience once its scheduled time arrives (`publisher_service.publish_approved_article`, meant to run periodically).
    - **Premium/auto-publish pipeline** (`run_premium_pipeline`, triggered by `POST /api/pipeline/start-premium`): runs the full pipeline for one domain (or `start-all` / "no domain" for every domain in the graph) and immediately publishes the article scheduled for tomorrow with `subscriber`-only audience, auto-approves the candidate, links the topic to its domain in the graph, and emails admins a summary report.
11. **Background execution** — every pipeline entry point spawns a daemon thread and tracks progress in the `pipeline_jobs` table (status: pending → running → completed/failed), pollable via `GET /api/pipeline/status/<job_id>`.
12. **Scheduling** — two GitHub Actions workflows (`.github/workflows/daily-pipeline.yml`, `premium-daily-pipeline.yml`) cron-trigger the deployed API daily (8:00 PM IST for the free pipeline, and a premium run) by POSTing to `PIPELINE_URL` / `PREMIUM_PIPELINE_URL` with a bearer token.

## Monetization

- **Subscriptions** are per-domain (or `all`) and backed by **Razorpay**: `app/services/razorpay_service.py` creates Razorpay plans/subscriptions; `app/routes/subscription_routes.py` exposes plan listing, subscribing (creates a Razorpay subscription and a `pending` row in `subscriptions`), a signed webhook (`/webhook`, HMAC-SHA256 verified against `RAZORPAY_WEBHOOK_SECRET`) that activates/renews/cancels subscriptions from Razorpay events, and a `/confirm` endpoint that re-fetches subscription status directly from Razorpay as a fallback to the webhook.
- **Team plans**: a subscription can be `is_team=true`, costs 4x, and is owned by a **workspace** (`app/models/workspace.py`, `app/routes/workspace_routes.py`) — any workspace member inherits access to that domain's content.
- **Access gating**: `GET /api/topics/today-topics?domain=...` returns the full article to subscribers and a teaser (150 chars + a "subscribe to unlock" prompt) to everyone else.

## Other features

- **AI tutor / inline explain** (`app/services/explain_service.py`, `POST /api/explain/`) — given a highlighted term and its surrounding paragraph, calls an LLM (GPT-4o-mini via GitHub Models inference endpoint, `GITHUB_TOKEN`) for a 3-sentence, plain-language explanation. Rate-limited to one call per 2 seconds process-wide (`app/utils/rate_limiter.py`) to control cost.
- **Auth** — Google Sign-In: the frontend sends a Google `id_token` to `POST /api/auth/google`; it's verified against `GOOGLE_CLIENT_ID` via `google-auth`, the user is upserted (`get_or_create_user`), and a first-party JWT (30-day expiry, HS256, `app/utils/jwt_utils.py`) is issued containing `user_id`, `email`, `role`. Protected routes use `require_auth` (validates the bearer JWT and loads the user) and `require_admin` (also requires `role == "admin"`). Pipeline trigger routes use `require_pipeline_secret` instead, which accepts a bearer token matching `PIPELINE_SECRET`/`CRON_SECRET`/`PIPELINE_TOKEN`, or allows localhost.
- **Admin review** — `app/routes/admin_candidate_routes.py` lets admins list pending/queued candidates and approve or reject them.
- **Email notifications** — `app/services/email_service.py` uses **Resend** to email admins whenever a new topic is generated, or a full domain-report after an all-domains run.

## Tech stack

- **Framework**: Flask 3 + Flask-CORS, served with Gunicorn in production.
- **Database**: PostgreSQL via `psycopg2` (`app/config/db.py`), connecting with SSL required and retrying transient connection failures. No ORM — hand-written SQL throughout `app/models/*`.
- **AI**: Google Gemini (`google-genai`, model `gemini-2.5-flash`) for article compilation; GPT-4o-mini (via GitHub Models) for the inline term explainer.
- **Search/scraping**: `ddgs` (DuckDuckGo search) + `trafilatura` (+ `beautifulsoup4`/`lxml` fallback) for content extraction.
- **TTS/media**: `edge-tts` for narration, `cloudinary` for audio hosting.
- **Payments**: `razorpay` SDK.
- **Email**: `resend`.
- **Auth**: `PyJWT` + `google-auth` (Google ID token verification).
- **Reliability**: `tenacity` for retries with exponential backoff around DB connects, Gemini calls, and Razorpay calls.

## Project structure

```
app/
  config/         # DB connection (db.py), JWT settings (jwt.py)
  jobs/           # In-memory job store + legacy threaded pipeline runner
  models/         # SQL access layer — one file per table/domain (users, plans,
                   # subscriptions, workspaces, concept graph, sources, candidates,
                   # published articles, pipeline jobs, ...)
  routes/         # Flask blueprints (one per resource, see API section)
  services/       # Business logic: pipeline orchestration, topic picking,
                   # fetching/scraping/cleaning, Gemini compilation, audio (TTS +
                   # Cloudinary), publishing, email, Razorpay, rate limiting
  utils/          # Auth decorators/middleware, JWT helpers, admin email lookup,
                   # rate limiter
run.py            # App factory / entry point, blueprint registration, CORS
seed_plans.py     # Seeds subscription plans into the `plans` table
scripts/          # Manual/dev test scripts (compilation dry-run, webhook simulator)
.github/workflows/  # Daily cron triggers for the free and premium pipelines
```

## Data model (PostgreSQL, created by `init_db()` in `app/models/schema.py`)

| Table | Purpose |
|---|---|
| `users`, `user_roles` | Registered users and their roles (`admin`, etc.) |
| `plans` | Subscription plans (domain, billing cycle, price, cached Razorpay plan id) |
| `subscriptions` | User/workspace subscriptions (status, dates, `is_team`, Razorpay ids) |
| `workspaces`, `workspace_members` | Teams and their members/roles, for team subscriptions |
| `concept_nodes`, `concept_edges` | The topic graph: `domain` nodes and `concept` nodes connected with weighted edges; source of all future topics |
| `topic_history` | Anti-repeat log of which topics were picked and when |
| `sources`, `topic_sources` | Discovered URLs, their scrape status/content, and their link to a topic |
| `daily_posts`, `daily_post_sources` | Legacy/earlier daily-post tables |
| `compiled_topics` | Raw Gemini-compiled JSON per topic |
| `article_candidate` | Pipeline output awaiting admin approval (pending/approved/rejected) |
| `published_articles`, `article_visibility` | Live articles and their audience (`public` vs `subscriber`) |
| `pipeline_jobs` | Background job status/result/error tracking |

## API reference

All routes return JSON. Auth is via `Authorization: Bearer <token>` — either a user JWT (`require_auth`/`require_admin`) or the pipeline secret (`require_pipeline_secret`).

### Auth — `/api/auth`
| Method | Path | Description |
|---|---|---|
| POST | `/google` | Exchange a Google ID token for a LoopLearn JWT (creates the user if new) |
| GET | `/me` | Current user profile + role + subscription context *(auth required)* |

### Topics — `/api/topics`
| Method | Path | Description |
|---|---|---|
| GET | `/today-topic` | Picks (but doesn't persist beyond history) an unwritten topic |
| GET | `/today-topics?domain=` | Today's published article for a domain; full content for subscribers, teaser otherwise *(auth required)* |

### Sources — `/api/sources`
| Method | Path | Description |
|---|---|---|
| POST | `/fetch` | Pick a topic, search the web, store + link sources |
| POST | `/scrape_latest` | Scrape the 20 most recently fetched sources |
| GET | `/topic/<topic_node_id>` | List sources linked to a topic |
| POST | `/topic/<topic_node_id>/scrape` | Scrape pending sources for a topic |
| GET | `/topic/<topic_node_id>/best` | Best-scored sources for a topic |
| GET | `/topic/<topic_node_id>/preview` | Preview of the top 3 scraped sources' text |
| GET | `/topic/<topic_node_id>/sections` | Structured section breakdown of the longest scraped source |

### Pipeline — `/api/pipeline`
| Method | Path | Description |
|---|---|---|
| POST | `/run` | Starts the free pipeline (creates a pending candidate) *(pipeline secret required)* |
| GET | `/status/<job_id>` | Poll a background job's status/result |
| POST | `/start-premium` | Starts the premium pipeline; body `{ "domain": "..." }`, or omitted for all domains |
| POST | `/start-all` | Starts the premium pipeline for every domain *(pipeline secret required)* |

### Admin candidates — `/api/admin/candidates` *(admin required)*
| Method | Path | Description |
|---|---|---|
| GET | `/` | List pending candidates |
| GET | `/queue` | List approved (scheduled) candidates |
| POST | `/approve/<candidate_id>` | Approve + schedule a candidate for publishing (default: tomorrow) |
| POST | `/reject/<candidate_id>` | Reject a candidate with a reason |

### Public articles — `/api/articles`
| Method | Path | Description |
|---|---|---|
| GET | `/today` | Today's public article |
| GET | `/<slug>` | A published article by slug |

### Subscriptions — `/api/subscriptions`
| Method | Path | Description |
|---|---|---|
| GET | `/plans` | List all subscription plans |
| POST | `/subscribe` | Create a Razorpay subscription for a plan (personal or team) *(auth required)* |
| POST | `/webhook` | Razorpay webhook receiver (HMAC-verified) — activates/renews/cancels subscriptions |
| GET | `/me` | Current user's active/most-recent subscription *(auth required)* |
| GET | `/me/today` | Today's article for the caller's subscribed domain *(auth required)* |
| GET | `/me/article/<slug>` | A specific article, gated to subscribers of its domain *(auth required)* |
| GET | `/me/list` | All of the caller's subscriptions *(auth required)* |
| POST | `/confirm` | Re-sync subscription status directly from Razorpay (webhook fallback) *(auth required)* |

### Workspaces — `/api/workspaces` *(auth required)*
| Method | Path | Description |
|---|---|---|
| POST | `/` | Create a workspace |
| GET | `/` | List the caller's workspaces (with team subscription + today's article) |
| GET | `/<workspace_id>` | Workspace details, members, subscription, today's article |
| POST | `/<workspace_id>/members` | Invite a member by email *(workspace admin only)* |
| DELETE | `/<workspace_id>/members/<user_id>` | Remove a member *(workspace admin only)* |
| DELETE | `/<workspace_id>` | Delete a workspace *(workspace admin only)* |

### Explain — `/api/explain`
| Method | Path | Description |
|---|---|---|
| POST | `/` | AI explanation of a highlighted term given surrounding context (rate-limited) |

### Misc
| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check ("Flask is running") |
| GET | `/api/test` | API health check |
| POST | `/api/init-db` | Creates all tables and seeds domain nodes |

## Setup

### Prerequisites
- Python 3.10+
- A PostgreSQL database (e.g. Neon, Supabase, or local Postgres)
- API keys/accounts for: Google Gemini, Google OAuth client, Cloudinary, Razorpay, Resend, GitHub Models (for the explain feature)

### Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configure environment

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# AI
GEMINI_API_KEY=...            # google-genai reads this automatically
GITHUB_TOKEN=...              # GPT-4o-mini via GitHub Models, used by /api/explain

# Auth
JWT_SECRET=...                # secret for signing LoopLearn JWTs
GOOGLE_CLIENT_ID=...           # Google OAuth client ID used to verify id_tokens

# Pipeline trigger auth (any one accepted as a bearer token)
PIPELINE_SECRET=...
CRON_SECRET=...
PIPELINE_TOKEN=...

# Cloudinary (audio hosting)
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

# Razorpay (subscriptions/payments)
RAZORPAY_KEY_ID=...            # or TEST_KEY_ID for sandbox
RAZORPAY_KEY_SECRET=...        # or TEST_KEY_SECRET for sandbox
RAZORPAY_WEBHOOK_SECRET=...

# Email (Resend)
RESEND_API_KEY=...

# Frontend
FRONTEND_URL=http://localhost:5173   # used to build post-payment redirect URLs
```

### Initialize the database

Start the app, then call the init endpoint once:

```bash
python run.py
curl -X POST http://localhost:5000/api/init-db
```

This creates every table and seeds the initial domain nodes in the concept graph. Optionally seed subscription plans:

```bash
python seed_plans.py
```

### Run

```bash
python run.py          # dev server on http://localhost:5000
# or, in production:
gunicorn run:app
```

### Trigger the pipeline manually

```bash
# Free pipeline — creates a candidate for admin review
curl -X POST http://localhost:5000/api/pipeline/run \
  -H "Authorization: Bearer $PIPELINE_SECRET"

# Premium pipeline for one domain — auto-publishes for tomorrow
curl -X POST http://localhost:5000/api/pipeline/start-premium \
  -H "Content-Type: application/json" \
  -d '{"domain": "System Design"}'

# Premium pipeline for every domain
curl -X POST http://localhost:5000/api/pipeline/start-all \
  -H "Authorization: Bearer $PIPELINE_SECRET"
```

Poll progress with:

```bash
curl http://localhost:5000/api/pipeline/status/<job_id>
```

### Scheduling in production

The two GitHub Actions workflows in `.github/workflows/` call the deployed pipeline endpoints on a cron schedule. Configure these repository secrets: `PIPELINE_URL`, `PREMIUM_PIPELINE_URL`, `PIPELINE_TOKEN`.

### Dev/test scripts

- `scripts/test_compilation_with_data.py` — exercises `topic_compiler.compile_topic` with mocked Gemini output.
- `scripts/test_webhook.py` — sends a signed mock Razorpay webhook to a running server (`--url`, `--user-id`, `--plan-id`, `--event`).
- `test.py` — prints a manually-issued admin JWT, useful for testing `require_pipeline_secret`/admin-only routes locally.
