# SkillPath — project context

## What this is
A full-stack web app that aggregates free course/tutorial content (starting
with YouTube) and generates a recommended learning path toward a skill goal
the user sets. It's a portfolio project for a 4th-year CS student targeting
a data-focused role (analyst/scientist/engineer), so the data pipeline
underneath the web app matters as much as the app itself — the goal is to
demonstrate real ingest → store → transform → serve work, not just CRUD.

## Working style — read this first
Treat the user as the client, not as another engineer pairing with you.
Before starting any new phase of work, ask what's needed rather than
assuming — this project is being run sprint by sprint, agile-style, with
the user making the calls on scope and priority. Keep sessions scoped to
one sprint's worth of work rather than jumping ahead.

## Tech stack
- Frontend: Next.js + Tailwind (chosen deliberately as something new to learn)
- Backend/pipeline: Python (FastAPI planned for the API layer; ingestion
  scripts are plain Python)
- DB: Postgres — Docker locally, Supabase planned for production (permanent
  free tier, and it bundles auth we'll need later — Neon was the other
  option considered but doesn't include auth)
- Orchestration: starting with a manual script / cron, upgrading to a
  scheduled job (GitHub Actions or Prefect) once ingestion is proven out
- Hosting constraint: free-tier only. Frontend → Vercel. Backend/DB →
  Supabase. Railway and Render's free Postgres tiers were ruled out
  (Railway's free plan is gone; Render's free DB expires after 30 days).

## Data sources
- YouTube Data API v3 — primary source. Free, 10,000 quota units/day. The
  Google Cloud OAuth consent screen was set to "Public data" (API key),
  not "User data" (OAuth) — this app only reads public video metadata, no
  user Google accounts involved.
- Coursera and Khan Academy were considered and ruled out: Coursera's
  catalog API requires a partner/affiliate agreement, and Khan Academy's
  public API is largely deprecated. A GitHub-hosted open curriculum
  dataset (e.g. freeCodeCamp's) is the planned second source.

## Database schema (Sprint 1 subset — see migrations/001_initial_schema.sql)
- `sources` — id, name, type
- `courses` — id, source_id FK, external_id, title, url, description,
  duration_minutes, difficulty, published_at, ingested_at
- `skills` — id, name, slug
- `course_skills` — course_id FK, skill_id FK, relevance_score (many-to-many)
- `ingestion_runs` — id, source_id FK, started_at, finished_at,
  records_ingested, status, error_message

Not yet built (later sprints): `users`, `user_goals`, `learning_paths`,
`path_steps` — these support goal-setting, generated paths, and progress
tracking once the ingestion side is solid.

## Roadmap
1. **Data ingestion foundation** — local Docker Postgres, schema
   migrations, YouTube ingestion script, ingestion_runs logging. ~1.5-2 wks.
2. **Backend and recommendation logic** — FastAPI endpoints, rule-based
   path ordering by difficulty/prerequisite tags. ~1 wk.
3. **Frontend MVP** — goal input, course browsing, path view, progress
   tracking. ~1.5-2 wks.
4. **Integration, auth, and deploy** — wire frontend to backend, basic
   auth, deploy to Vercel + Supabase. ~1 wk.
5. **Orchestration and polish** — scheduled ingestion job, error handling,
   README/architecture docs. ~3-5 days.
6. **Stretch** — embedding-based recommendation similarity, analytics view
   on most-requested skills and completion trends. Optional, post-MVP.

## Current status: Sprint 1, in progress
Delivered so far (already in this repo, or ready to be added):
- `docker-compose.yml` — local Postgres
- `migrations/001_initial_schema.sql` — the five tables above
- `.env.example` — DATABASE_URL, YOUTUBE_API_KEY
- `requirements.txt` — psycopg, python-dotenv, requests
- `scripts/ingest_youtube.py` — pulls videos for a topic via YouTube Data
  API v3, normalizes into `courses`, logs every run to `ingestion_runs`
- `scripts/check_db.py` — sanity check: course counts by source, last 5
  ingestion runs
- `SPRINT1_README.md` — setup steps in order

Sprint 1 backlog remaining:
- [x] User set up the Google Cloud project + YouTube Data API key
      (`.env` created with real `YOUTUBE_API_KEY`, "Public data" type,
      restricted to YouTube Data API v3)
- [x] Ran `docker compose up -d` — `skillpath_db` container healthy on
      port 5432 — and applied `migrations/001_initial_schema.sql`; all 5
      tables (`sources`, `courses`, `skills`, `course_skills`,
      `ingestion_runs`) confirmed present via `\dt`
- [ ] Run `scripts/ingest_youtube.py` with the real key and confirm real
      rows land in `courses`
- [ ] Confirm `scripts/check_db.py` shows correct counts and a `success`
      row in `ingestion_runs`

## Immediate next step
Once the API key works end to end and Sprint 1's Definition of Done is
met (Docker running, schema applied, one successful ingestion run
logged), the next conversation should be Sprint 2 planning: the FastAPI
backend and the rule-based recommendation/path-ordering logic. Ask the
user to confirm Sprint 1 is fully working before scoping Sprint 2 — don't
assume it's done just because the code exists.
