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

## Current status: Sprint 4 DONE on branch `worktree-sprint4-auth-deploy` (not yet merged) — `main`/`dev-branch` still reflect everything through the Sprint 3 audit-fix pass

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

### Sprint 3: DONE, merged into `dev-branch` and pushed
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
- Merged into `dev-branch` (fast-forward) and pushed to origin. Worktree
  and branch cleaned up per the usual finishing-a-development-branch flow.

### Dev/prod tooling: added after Sprint 3, on `dev-branch`
Root `package.json` (`npm run dev:backend`/`dev:frontend`/`dev:full` via
`concurrently`), `start-sp.bat`/`stop-sp.bat` (wrap the existing dev
`docker-compose.yml`), and a new local-only production-build smoke-test
stack: `docker-compose.prod.yml` + `backend/Dockerfile` +
`frontend/Dockerfile` (Next.js `output: "standalone"`) +
`start-sp-prod.bat`/`stop-sp-prod.bat`. This is NOT the real deployment
path — actual deploy stays Vercel (frontend) + Supabase (backend/DB) per
the Hosting constraint above; the prod compose stack exists only so a
production build can be sanity-checked locally before shipping. Prod
runs on ports 8001 (backend)/3001 (frontend)/5433 (db) — deliberately
different from dev's 8000/3000/5432 to prevent the two stacks from
colliding (an actual incident during initial build: both compose files
implicitly shared a Docker Compose project name and both defined a
service called `db`, and running prod once destroyed dev's Postgres
container — data survived via the named volume, but the fix,
`name: skillpath-prod` as an explicit top-level key in
`docker-compose.prod.yml` only, is why dev's compose file deliberately
has NO explicit project name — adding one there would rename its volume
and orphan existing dev data). Prod's DB auto-applies `migrations/*.sql`
via `docker-entrypoint-initdb.d`, and `start-sp-prod.bat` always tears
down with `-v` before rebuilding, so every run reflects the current
migrations rather than a possibly-stale first-boot schema.

### Post-Sprint-3 full-system audit + fix pass: DONE, merged into `dev-branch` and `main`, both pushed
After Sprint 3 merged and the tooling above was built, the user asked for
a full bug/correctness audit of the whole system (not tied to a specific
sprint) — three parallel opus-model reviews covering backend/pipeline,
frontend, and the brand-new dev/prod tooling, followed by fixes for
every Critical and Important finding (Minor findings were left
deferred, not part of this pass).

**2 Critical bugs found and fixed, both already live in the shipped
app:**
1. The YouTube API key was appearing in `ingestion_runs.error_message`
   and stdout on any HTTP error (including ordinary quota exhaustion),
   because `requests`' exception messages include the full request URL
   and the key rides in the query string (YouTube Data API v3 has no
   header-based key auth, so the key can't be moved out of the URL —
   the fix redacts it from any message before it's persisted or
   printed, in `scripts/ingest_youtube.py`).
2. Video durations ≥24 hours parsed to 0 minutes (the ISO-8601 day
   component, e.g. `P1DT2H`, wasn't handled, and `re.match` let it fail
   silently). This was live and actively corrupting the recommendation
   ranking: a real 30-hour "SQL Full Course for Beginners" was recorded
   at `duration_minutes = 0` and therefore sorted as the single best
   beginner course. The parser is fixed (day component handled,
   `re.fullmatch` so garbage fails loudly, `None` instead of `0` for
   genuinely unparseable input) and tested. The parser fix alone only
   prevents the bug going forward, so after the user confirmed, a real
   re-ingestion was run against all three seeded skills (`sql`,
   `python`, `statistics` — same topics as Sprint 2:
   `scripts/ingest_youtube.py --topic "..." --skill ... --max-results 25`)
   to correct existing data. Confirmed fixed: the "SQL Full Course for
   Beginners (30 Hours)" row now reads `duration_minutes = 1788`
   (≈29.8 hrs, correct), and no course in the DB is at 0 minutes anymore.

**16 Important findings fixed, split across the three review domains**
(all individually reviewed clean, 3 needed their own fix round):
- Backend: CORS origin hardcoded (now `CORS_ORIGINS` env var, correctly
  loaded via `load_dotenv()` after a fix-round correction); failed
  ingestion runs reported 0 records despite partial data already
  committed (now tracks a real running counter); `course_id` wasn't
  validated as a UUID, causing a raw 500 instead of a clean 404/422 (now
  typed `uuid.UUID`); plain `pytest` failed without `-m` (new root
  `conftest.py`); unguarded list-indexing in tests produced cryptic
  `IndexError`s on an empty DB instead of readable failures. Test suite
  grew from 15 to 23.
- Frontend: course-detail page had no stale-response guard (same race
  class Task 10 fixed elsewhere in Sprint 3, missed here — now uses the
  same `requestIdRef` pattern as `browse/page.tsx`); `useLocalPath`
  trusted a type-cast on parsed localStorage JSON with zero shape
  validation, meaning any future `StoredPath` schema change (guaranteed
  by the roadmap) would brick every returning user's saved path with no
  recovery (now validates shape, returns `null` on mismatch); a
  zero-course step (the seeded `data-visualization` fixture) could never
  be marked complete, permanently jamming "steps left" and the
  current-step highlight (now vacuously complete, with a visually
  distinct "no courses yet" marker); `clearPath` existed but nothing
  called it, and re-onboarding into the same goal silently wiped
  progress (now a "Change goal" control on the profile page, and
  `savePath` preserves progress when the goal slug is unchanged);
  profile and course-detail pages didn't gate on the `isLoaded` flag
  `page.tsx` already used, flashing wrong content on every load (now
  fixed); `npm run lint` had 2 errors from the SSR-safe-hydration
  pattern (now targeted disable comments, not a bigger rewrite); "Mark
  as complete" was enabled and silently no-op'd for courses reached via
  Browse that weren't part of the saved path (now disabled with an
  honest label in that case).
- Tooling: `.dockerignore` patterns lacked `**/` prefixes so they didn't
  match at any depth like `.gitignore` does (fixed, both root and
  frontend); backend Docker image pinned a different Python minor
  version than the dev venv (now matched, `python:3.14-slim`); dev/prod
  port collision (see tooling section above); `.bat` scripts had no
  error visibility (window just closed on failure — now `cd /d`,
  `pause` on error, and real exit codes); `npm run dev:full` didn't
  start Postgres first; prod credentials were triplicated with an
  asymmetric footgun (now single-sourced via Compose interpolation). A
  fix-round caught two gaps the first pass missed: `frontend/.dockerignore`
  hadn't gotten the same `**/` depth-anchoring as the root file, and
  `start-sp-prod.bat`'s `down -v` step had no error check before
  proceeding to `up`, which could silently defeat the whole
  fresh-migrations guarantee.
- Full backend test suite: 23/23 passing. Frontend: `npm run build` and
  `npm run lint` both clean.
- Deliberately deferred (Minor, not part of this pass — see the three
  reports under `docs/superpowers/fixes/` for the complete lists): N+1 query
  pattern in `list_courses`; various accessibility gaps (ARIA labels,
  progress-bar semantics); `useLocalPath` giving each caller an
  independent state copy (no cross-instance sync, currently harmless);
  no confirmation dialog on the new "Change goal" control despite it
  being destructive to progress on a different goal; several smaller
  polish items across all three domains.

### Sprint 4: IN PROGRESS — auth, data migration, deploy prep
Design spec: `docs/superpowers/specs/2026-09-06-sprint4-auth-deploy-design.md`.
Implementation plan: `docs/superpowers/plans/2026-09-06-sprint4-auth-deploy.md`
(13 tasks). Being built via subagent-driven-development on branch
`worktree-sprint4-auth-deploy` in the git worktree at
`.claude/worktrees/sprint4-auth-deploy`, forked from `dev-branch`.

**Precondition setup:** `scripts/setup-sprint4-dev.sh` (a `/wizard`-generated
interactive script, currently untracked — not yet decided whether to commit
it) walks through: Supabase CLI via `npx`, `supabase init`, creating a
hosted Supabase project, `supabase login`/`link`, and starting the local
CLI stack (Postgres + Auth + Studio, replacing the old Docker-only
Postgres). Run once already; `.env`/`frontend/.env.local` have the
resulting keys.

**Local dev stack changed:** `npx supabase start`/`stop`/`status` replaces
`docker-compose.yml` for local dev entirely (Task 1) — the local Supabase
CLI stack provides both Postgres (port 54322) and a real Auth service.
Migrations moved from `migrations/*.sql` to `supabase/migrations/`,
applied via `npx supabase db reset`.

**Tasks 1-11 complete, individually reviewed clean:**
1. Migrations relocated to Supabase CLI layout, Docker Postgres retired
2. `user_goals`/`completed_courses` schema added (references
   Supabase's own `auth.users`)
3. `backend/auth.py`'s `get_current_user_id` JWT dependency + real test
   auth fixtures (hitting the local Supabase Auth admin API, no mocks)
4. User-progress query functions + `PathStep` moved to `backend/schemas.py`
5. `POST /paths` now requires auth, persists the resolved goal
6. New `GET/POST/DELETE /me/*` endpoints for the authenticated user's
   own path/progress
7. Frontend Supabase client + auth-aware `api.ts` functions
8. `/login`/`/signup` screens
9. Route protection (`useRequireAuth`) on the hub layout + onboarding
10. `useServerPath` hook replaces `useLocalPath`; onboarding simplified
    (backend now persists the goal automatically)
11. Dashboard/profile/course-detail screens migrated to `useServerPath`

**Critical bug found and fixed via live end-to-end testing, not caught
by any automated test:** after Task 11, a real signup → onboarding →
"Data analyst" flow through the actual UI failed with "Something went
wrong" — `POST /paths` 401'd even with a real, unexpired, correctly-
attached session token. Root cause: the local Supabase CLI (2.116.0)
issues **ES256-signed** (asymmetric) JWTs by default via its own JWKS
endpoint, not the shared HS256 secret Task 3's plan assumed ("local
dev's CLI stack uses HS256 by default" — true of older CLI versions,
false of this one). `backend/auth.py` only accepted HS256, rejecting
every real user's token, while all 33 backend tests passed regardless
— they used `tests/auth_helpers.make_test_jwt`, which forged synthetic
HS256 tokens that never touched real signing infrastructure. This is
exactly the class of bug a test suite built entirely on synthetic auth
tokens cannot catch.

Fixed: `backend/auth.py` now verifies via the local JWKS endpoint
(`PyJWKClient`, ES256), `tests/auth_helpers.get_access_token` replaces
`make_test_jwt` with a real password-grant sign-in against the local
Auth API (so tests exercise the real path from now on). Confirmed fixed
via a second live signup → onboarding → dashboard run. A follow-up
security review (opus, 7 explicit checks — algorithm-confusion
resistance, audience validation, kid-based key lookup, fail-open
analysis, JWKS endpoint trust, exception handling, test coverage) found
**zero Critical findings** — the verification logic is sound — plus 7
Important hardening/observability findings; 5 were fixed in one round
(broader exception handling, logging on verification failure, two new
tests closing real coverage gaps, removing a now-dead
`SUPABASE_JWT_SECRET` prompt from the setup wizard), re-reviewed clean.
2 deliberately deferred to Sprint 4's deploy-prep work (Task 13 note
below): enforcing `required` JWT claims (`exp`/`sub`) as defense-in-
depth, and caching the `PyJWKClient` at module scope instead of
constructing one per request (currently a real, if minor, DoS surface
— an unauthenticated request with a bogus `kid` costs two outbound
JWKS fetches to the Auth service).

Full backend test suite: 34/34 passing. Frontend `npm run build` clean.

**Tasks 12-13 complete.** Task 12 added the sign-out control on the
profile page. Task 13 pointed the local prod-smoke-test Docker stack's
backend at the Supabase CLI stack via `host.docker.internal` — its own
Postgres container can't run Supabase Auth. Task 13 also surfaced (but
didn't fix, per its brief) that the prod stack's *frontend* container
failed to build: a `frontend/package-lock.json` cross-platform drift
(missing `@emnapi/runtime`/`@emnapi/core` entries needed under Linux,
since the lockfile had only ever been regenerated via `npm install` on
Windows) made `npm ci` fail inside `node:22-slim`.

**Full live end-to-end browser test** (real signup → onboarding →
"Data analyst" goal → dashboard rendered the real path → marked a
course complete → hard refresh confirmed server persistence → logged
out → confirmed `/profile` redirects to `/login`, session actually
cleared server-side) passed after Task 13.

**Prod smoke-test frontend build fixed** (post-Task-13, pre-final-review):
regenerated `frontend/package-lock.json` from inside a `node:22-slim`
container (matching the Dockerfile's actual build platform, not the
Windows host) to pick up the missing Linux-only optional dependency
entries; separately, `docker-compose.prod.yml` had never passed
`NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY` as frontend
build args (only `NEXT_PUBLIC_API_BASE_URL` was wired), so the Next.js
build failed at prerender for lack of those env vars even after the
lockfile fix — added the missing `ARG`/`ENV` pairs to
`frontend/Dockerfile` and wired the build args from the existing
`SUPABASE_LOCAL_URL`/`SUPABASE_LOCAL_ANON_KEY` root `.env` values,
matching the audit-fix pass's single-sourced-credentials pattern.
Verified: full `docker compose -f docker-compose.prod.yml up -d --build`
succeeds, backend and frontend both serve correctly (200 on `/docs`,
`/`, `/login`) against the real local Supabase CLI stack.

**Final whole-branch review (opus)** found zero Critical issues — the
JWT verification core and per-user data scoping (no IDOR surface
anywhere; every `/me/*`/`/paths` query derives `user_id` only from the
verified token, never a client-supplied value) were both confirmed
sound. Route protection was confirmed complete across every `(hub)`
route and `/onboarding`, and no Sprint-3-era `localStorage`/
`useLocalPath` reference or drive-by redesign survived anywhere in the
migrated screens. 6 Important findings, all fixed in one round and
re-verified (36/36 backend tests passing, up from 34; `npm run build`
clean; `npm run lint` shows only the one pre-existing non-blocking
warning already known from Task 9's brief):
- The two JWT-hardening items explicitly deferred to Task 13 (above)
  had in fact gone unaddressed — fixed now: `backend/auth.py` caches
  its `PyJWKClient` at module scope instead of constructing one per
  request (the DoS surface: every request was refetching the whole
  JWKS, not just ones with a bogus `kid`), and `jwt.decode()` now
  requires the `exp`/`sub` claims.
- `POST /me/progress`'s `course_id` was a plain `str`, inconsistent
  with `GET /courses/{id}`'s `uuid.UUID` typing from the post-Sprint-3
  audit — a malformed or nonexistent id hit an unhandled FK violation
  and surfaced as a raw 500. Now typed `uuid.UUID`, with the FK
  violation caught and turned into a clean 404. Two new tests cover
  both cases.
- `useServerPath`'s mount-time fetch let any non-404 failure (a
  transient 500, a network blip) propagate as an unhandled promise
  rejection, leaving the user staring at a blank Landing screen with no
  error message — this backed every migrated screen, so the gap was
  systemic. Now surfaces an `error` string, wired into `/`, `/profile`,
  and `/course/[id]` with the same `text-red-600` pattern already used
  elsewhere.
- `/login` redirected unconditionally to `/onboarding` on success, even
  for a returning user with an existing goal — funneling them back
  through the goal picker instead of their dashboard, and a latent
  goal-clobber risk once a second goal exists. Now redirects to `/`,
  which already correctly branches Dashboard vs. Landing.
- `.env.example`/`frontend/.env.local.example` had never been updated
  since Task 1 retired the plain-Postgres container — still showed the
  old port 5432 and had no Supabase variables at all. Now documents the
  Supabase CLI local-stack variables and the new port 54322.
- `SPRINT1_README.md` still instructed `docker compose up -d` and
  `psql ... < migrations/001_initial_schema.sql`, both retired by
  Task 1. Now marked historical, pointing at
  `scripts/setup-sprint4-dev.sh` for current setup.

4 Minor findings deliberately deferred (not part of this pass): a
check-then-act race in `toggle_completed_course` (`ON CONFLICT DO
NOTHING` would close it, low real-world likelihood); a stale
Sprint-3-era comment wording in `course/[id]/page.tsx` (fixed anyway,
it was a one-line change alongside the error-handling fix in the same
file); the known non-blocking `useRequireAuth.ts` lint warning; no
shared auth/path context across hub routes (each screen independently
calls `useServerPath`/`useRequireAuth` — same "no cross-instance sync"
class already deferred for `useLocalPath` in the Sprint 3 audit,
harmless at current scale).

**Sprint 4 implementation is complete.** Not yet merged into
`dev-branch` — see "Immediate next step" below for what's left
(finishing the branch, and the still-open question of whether
`scripts/setup-sprint4-dev.sh` and `supabase/` should be committed).

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
Sprint 4 (all 13 planned tasks, the live E2E pass, the prod smoke-test
frontend fix, and the final whole-branch review's fix round) is
complete on branch `worktree-sprint4-auth-deploy` in the git worktree
at `.claude/worktrees/sprint4-auth-deploy` — **not yet merged** into
`dev-branch` or `main`. The SDD ledger at
`.claude/worktrees/sprint4-auth-deploy/.superpowers/sdd/2026-09-06-sprint4-auth-deploy/progress.md`
has the full task-by-task narrative record.

What's left before this sprint is fully closed out:
- Finish the branch (merge into `dev-branch`, per the usual
  `finishing-a-development-branch` flow — ask the user which option
  they want, same as Sprints 2/3).
- Decide whether `scripts/setup-sprint4-dev.sh` (the `/wizard`-generated
  precondition setup script) and the `supabase/` directory itself
  (currently both untracked, per `git status`) should be committed as
  project tooling — never resolved during implementation.
- Real deployment (Decision 8 in the spec: Vercel + Render + hosted
  Supabase project, account creation and key-copying is user setup
  work) has not started — everything above is local-dev-only.

Sprints 1-3, dev/prod tooling, the audit-fix pass, and the corrective
re-ingestion remain merged into both `dev-branch` and `main` and pushed
to origin, unaffected by Sprint 4's worktree.

The Sprint 3-era open question — migrating `StoredPath`'s client-only
localStorage shape to server-persisted progress once real user accounts
exist — is what Sprint 4 already did, so it's resolved rather than
still open. Ask the user before scoping any further work beyond
finishing/merging this branch and the real deployment step — don't
assume priorities. Also fair game whenever the user wants them,
independent of the auth work: the Profile/Browse deferrals from
Sprint 3 (streak/badges, trending sections), the 4 Minor items deferred
from this sprint's final review (see the "Current status" section
above), and the Minor items deferred from the post-Sprint-3 audit pass
(see `docs/superpowers/fixes/` for the full lists).
