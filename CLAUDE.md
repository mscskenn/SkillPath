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
   tracking, built to the full visual/UX design in
   `docs/superpowers/specs/DESIGN.md`. Screens: landing page, onboarding
   (goal input), dashboard (path view), search/browse (course browsing),
   course detail, profile (progress tracking), plus the shared
   layout/nav and Tailwind theme (colors, typography, mobile-first
   rules) all of those sit on. Login/signup is explicitly OUT of this
   sprint — it needs real auth, deferred to Sprint 4. DONE, on
   `dev-branch` — see "Current status" below.
4. **Integration, auth, and deploy** — wire frontend to backend, basic
   auth, deploy to Vercel + Supabase. Now includes building the
   login/signup screen from `docs/superpowers/specs/DESIGN.md` (deferred
   from Sprint 3 since it needs auth to be meaningful). ~1 wk, likely
   understated now that a screen moved here.
5. **Orchestration and polish** — scheduled ingestion job, error handling,
   README/architecture docs. ~3-5 days.
6. **Stretch** — embedding-based recommendation similarity, analytics view
   on most-requested skills and completion trends. Optional, post-MVP.

## Current status: Sprint 3 frontend complete, on worktree branch pending merge decision

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

### Sprint 3: DONE, on branch `worktree-sprint3-frontend`, not yet merged
Full Next.js frontend (App Router, TypeScript, Tailwind v4) plus two new
FastAPI backend endpoints, designed and built via the superpowers
brainstorming → writing-plans → subagent-driven-development flow:
- Design spec: `docs/superpowers/specs/2026-09-06-sprint3-frontend-mvp-design.md`
- Implementation plan: `docs/superpowers/plans/2026-09-06-sprint3-frontend-mvp.md`
- Built on branch `worktree-sprint3-frontend`, forked from `dev-branch`
  (not `main` — this project switched to `dev-branch` as the active
  working branch after Sprint 2), in the git worktree at
  `.claude/worktrees/sprint3-frontend`.
- Backend additions: `backend/schemas.py` (shared Pydantic models,
  extracted from `routers/paths.py`), CORS middleware in `backend/main.py`
  (allows `http://localhost:3000`), `GET /courses` (paginated search/
  browse, bounded `limit`/`offset`), `GET /courses/{id}` (detail). Test
  suite grew from 8 to 15 (`tests/test_cors.py`, `tests/test_courses.py`).
- Frontend: `frontend/` — shared nav layout scoped to a `(hub)` route
  group (`/`, `/browse`, `/course/[id]`, `/profile`), with `/onboarding`
  correctly outside it per the design spec; `frontend/lib/api.ts` (typed
  fetch client) and `frontend/lib/useLocalPath.ts` (the integration seam
  every screen depends on); 5 screens: landing (folded into `/` when no
  path is saved), onboarding, dashboard, browse, course detail, profile.
- **No backend persistence for progress/paths this sprint — deliberate.**
  Selected goal + step-completion state lives in the browser's
  `localStorage` only (key `skillpath.currentPath`), per the design
  spec's Decision 1. This is why `users`/`user_goals`/`learning_paths`/
  `path_steps` are still not built (see Database schema section above) —
  Sprint 4's auth work will need to design the migration from this
  client-only shape to server-persisted progress.
- All 12 plan tasks complete, each individually reviewed (5 needed a
  fix round — Task 6's nav wasn't actually pinned to the bottom on
  mobile, Task 8's copy was all-lowercase against DESIGN.md's sentence-
  case rule, Task 9's dashboard had 3 real gaps — wrong "steps left"
  count, missing "current step" visual state, missing "estimated time"
  stat — Task 10 had an unguarded stale-response race in the debounced
  search, Task 11 didn't reset error/course state between course
  navigations). All fixed and re-verified clean.
- **Final whole-branch review (opus) found 6 Important cross-task
  issues** no single task's review could see, all fixed in one follow-up
  pass and re-verified clean: a leftover scaffold dark-mode CSS block
  fought the light design's Tailwind classes (unreadable in dark-mode
  browsers); `/onboarding` was rendering inside the shared nav layout
  (fixed via the `(hub)` route group restructuring); the hub route
  flashed the marketing landing page before the dashboard on every load
  for returning users (fixed with an `isLoaded` flag on
  `useLocalPath`); "Mark as complete" was a silent no-op when reached
  via Browse without ever doing onboarding (now disabled with
  explanatory copy in that case); a sentence-case fix from the task
  review rounds over-corrected some mid-phrase numeral-first stat
  strings (e.g. "3 Courses done" should read "3 courses done" — fixed,
  and made consistent with Dashboard's already-correct lowercase style);
  this CLAUDE.md itself wasn't updated for Sprint 3 by any task (no
  task existed for it — this section is that fix).
- Deferred, not built this sprint (recorded here per the final review's
  recommendation, since nothing else durable was tracking them): the
  Profile screen's day-streak stat and badges row (DESIGN.md §5) — genuinely
  needs timestamps `StoredPath` doesn't carry, a real design decision for
  a later sprint, not an oversight; the Browse screen's "Trending now"/
  "Most sought-after" editorial sections (DESIGN.md §5) — explicitly out
  of scope per the design spec, since the backend only serves ingested
  course data, not curated trend lists; several small backend/frontend
  polish items (N+1 query pattern in `list_courses`, no UUID-format
  validation on `course_id`, no ARIA labels on a couple of inputs) — see
  the plan's SDD ledger for the full list before it's deleted, or ask
  for a summary if it's already gone.
- Full test suite: 15/15 passing (`venv/Scripts/python.exe -m pytest -v`)
  and `npm run build` clean, both re-verified after the final-review fix
  wave — local Docker Postgres (`skillpath_db`) must be up for backend
  tests.
- Not yet decided: merge into `dev-branch` now, push + PR, or keep
  iterating — same "don't merge unilaterally" discipline as every prior
  sprint.

## Design spec (drives Sprint 3 and part of Sprint 4)
`docs/superpowers/specs/DESIGN.md` is the source of truth for the
project's UI/UX: target audience (budget-conscious students, mobile
first), design principles, visual system (flat, bordered rows over
cards, pill badges, one accent color per view), full screen-by-screen
specs for all 7 screens, mobile-specific layout rules, key UI copy, and
the Next.js/TypeScript/Tailwind implementation notes. It was written
covering the whole app, not one sprint — see the Roadmap section above
for how its 7 screens are split across Sprint 3 (6 screens + visual
system) and Sprint 4 (login/signup). Read it before starting any
frontend screen work; it's the layout/spacing/color/copy source of
truth, not the code itself (mockups were built in a separate tool).

## Immediate next step
**Do not assume Sprint 3 is merged just because it's implemented and
reviewed clean.** When the user comes back to this:
1. Check whether `.claude/worktrees/sprint3-frontend` still exists and
   what state it's in (`git -C .claude/worktrees/sprint3-frontend
   status`, `git -C .claude/worktrees/sprint3-frontend log --oneline
   -10`) — same discipline as every prior sprint.
2. Ask the user whether they want to merge `worktree-sprint3-frontend`
   into `dev-branch` now, push it and open a PR, or keep iterating on it
   first — don't merge unilaterally.
3. Once Sprint 3 is actually on `dev-branch` and confirmed working, the
   next planning conversation is Sprint 4: auth (Supabase), the
   login/signup screen (DESIGN.md's 7th screen, deferred here), wiring
   the frontend to real auth, and — the biggest open design question —
   migrating `StoredPath`'s client-only localStorage shape to
   server-persisted progress once real user accounts exist. The two
   Profile/Browse deferrals noted above (streak/badges, trending
   sections) are also fair game to pick up whenever the user wants them,
   independent of the auth work.
