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

## Database schema
Sprint 1 (see migrations/001_initial_schema.sql, applied to main's local DB):
- `sources` — id, name, type
- `courses` — id, source_id FK, external_id, title, url, description,
  duration_minutes, difficulty, published_at, ingested_at
- `skills` — id, name, slug
- `course_skills` — course_id FK, skill_id FK, relevance_score (many-to-many)
- `ingestion_runs` — id, source_id FK, started_at, finished_at,
  records_ingested, status, error_message

Sprint 2 (see migrations/002_goals.sql, merged into main):
- `goals` — id, name, slug
- `goal_skills` — goal_id FK, skill_id FK, step_order (many-to-many,
  ordered — this is what makes a "path" a sequence of skills)

Not yet built (later sprints): `users`, `user_goals`, `learning_paths`,
`path_steps` — these support user-submitted goals and progress tracking.

## Roadmap
1. **Data ingestion foundation** — local Docker Postgres, schema
   migrations, YouTube ingestion script, ingestion_runs logging. ~1.5-2 wks.
2. **Backend and recommendation logic** — FastAPI endpoints, rule-based
   path ordering by difficulty/prerequisite tags. ~1 wk. DONE, on `main`
   — see "Current status" below.
3. **Frontend MVP** — goal input, course browsing, path view, progress
   tracking. ~1.5-2 wks.
4. **Integration, auth, and deploy** — wire frontend to backend, basic
   auth, deploy to Vercel + Supabase. ~1 wk.
5. **Orchestration and polish** — scheduled ingestion job, error handling,
   README/architecture docs. ~3-5 days.
6. **Stretch** — embedding-based recommendation similarity, analytics view
   on most-requested skills and completion trends. Optional, post-MVP.

## Current status: Sprint 2 backend merged into main

### Sprint 1: DONE, on `main`
Repo is on GitHub (`github.com/mscskenn/SkillPath`, `main`, `.env`
gitignored and never committed). Delivered: `docker-compose.yml`,
`migrations/001_initial_schema.sql` (the five Sprint 1 tables),
`.env.example`, `requirements.txt`, `scripts/ingest_youtube.py`,
`scripts/check_db.py`, `SPRINT1_README.md`. Local Postgres running,
schema applied, one real successful ingestion run logged (25 SQL videos).
Definition of Done met and confirmed by the user.

### Sprint 2: DONE, merged into main
Full backend (FastAPI `POST /paths` recommendation endpoint) was designed
and built via the superpowers brainstorming → writing-plans →
subagent-driven-development flow:
- Design spec: `docs/superpowers/specs/2026-09-06-sprint2-backend-design.md`
- Implementation plan: `docs/superpowers/plans/2026-09-06-sprint2-backend.md`
- Was built on branch `worktree-sprint2-backend` in a git worktree; user
  chose to merge into `main` (fast-forward, no conflicts), tests re-run
  green on `main` (8/8) after merge, worktree removed and branch deleted
  (finishing-a-development-branch skill, option 1).
- All 6 plan tasks complete and individually code-reviewed clean:
  1. `migrations/002_goals.sql` — `goals`/`goal_skills` schema + seed data
     (one seeded goal, `data-analyst` → sql → python → statistics →
     data-visualization, the last deliberately left with zero ingested
     courses as a test fixture)
  2. `classify_difficulty()` heuristic added to `scripts/ingest_youtube.py`
  3. Ingestion script re-run for real against sql/python/statistics
     (25 courses each, difficulty + skill tagged)
  4. `backend/db.py` + `backend/queries.py` — raw-SQL data access layer
  5. `backend/routers/paths.py` + `backend/main.py` — the `POST /paths`
     endpoint itself
  6. `tests/test_paths.py` — integration tests against the real DB
- Final whole-branch review (opus) found 1 Important + 1 must-fix
  (both fixed, re-reviewed clean) and 7 Minor findings left deliberately
  deferred (documented in the plan's SDD ledger, which no longer exists
  on disk — the ledger was deleted after the clean final review per the
  subagent-driven-development skill's normal cleanup; the deferred items
  worth remembering: no root `conftest.py`/pytest config yet, no `LIMIT`
  on courses-per-skill, no `UNIQUE(goal_id, step_order)` constraint, no
  connection pooling, no CORS — none are blockers, most are things
  Sprint 3's frontend work will force a decision on anyway).
- Full test suite: 8/8 passing on `main` (`venv/Scripts/python.exe -m
  pytest -v`) — local Docker Postgres (`skillpath_db`) must be up first,
  ingestion/backend tests hit the real DB, not mocks.
- Note: `main`'s venv did not have the Sprint 2 backend/test deps
  installed until the merge — `pip install -r requirements.txt` was run
  against `main`'s venv as part of verifying the merged result.
- Local commits are ahead of `origin/main` (not yet pushed) — not pushed
  or PR'd, per user's choice to merge locally only.

## Immediate next step
Sprint 2 is confirmed done and on `main` — worktree and branch cleaned
up, tests green. Next planning conversation is Sprint 3: the Next.js
frontend MVP (goal input, course browsing, path view, progress
tracking). Ask the user before scoping it — don't assume priorities.
It will need CORS on the FastAPI app and a decision on the deferred
`LIMIT`-per-skill question (both noted above as deferred from Sprint 2).
