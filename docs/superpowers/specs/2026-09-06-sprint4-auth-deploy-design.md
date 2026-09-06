# Sprint 4 — Auth, data migration, and deploy design spec

## Context

Sprints 1-3 (data ingestion, FastAPI backend, Next.js frontend) are done,
merged, and a full-system audit-fix pass has landed on both `main` and
`dev-branch`. Sprint 3's frontend has no authentication — anyone can set a
goal and track progress, stored entirely in the browser's `localStorage`
(see `docs/superpowers/specs/2026-09-06-sprint3-frontend-mvp-design.md`,
Decision 1). Per the roadmap in `CLAUDE.md`, Sprint 4 was always scoped to
bundle three things together: auth, wiring the frontend to real auth, and
deploying to Vercel + Supabase. This spec covers the decisions needed to
actually build that.

This spec assumes a fresh Supabase project, Render account, and Vercel
account do not exist yet — account creation and copying resulting
keys/URLs is work only the user can do, mirroring how the YouTube API key
was set up in Sprint 1.

## Goals

- Real user accounts via Supabase Auth (email/password), with custom
  login/signup screens per `DESIGN.md`'s spec (its 7th and final screen).
- Login required before onboarding — matches `DESIGN.md`'s literal flow
  (`Landing → Log in/sign up → Set goal → Dashboard`), and avoids needing
  to design a migration path for pre-existing anonymous localStorage data.
- Replace the `localStorage`-only progress model with server-persisted
  data (`user_goals`, `completed_courses` tables), scoped per user.
- Deploy: frontend to Vercel, backend to a free-tier host that actually
  runs FastAPI (Supabase does not — see Decision 1), Postgres + Auth on
  Supabase's hosted project.

## Non-goals

- Google OAuth — deferred. Email/password only this sprint; Google
  sign-in can be added later without disrupting the data model (Supabase
  Auth supports multiple providers per user without a schema change).
- Anonymous browsing / an anonymous-to-account data migration path —
  deferred by construction, since login is required before onboarding.
  Any pre-existing browser localStorage data from Sprint 3 testing is
  simply orphaned, not migrated.
- Any visual/UX redesign of onboarding, dashboard, browse, course detail,
  or profile — those screens' data source changes (server instead of
  `localStorage`), not their design, copy, or layout.
- Password reset / email verification flows — Supabase Auth supports
  these out of the box, but building custom UI for them is out of scope
  this sprint unless trivially free (e.g. Supabase's default email
  templates firing automatically requires no extra frontend work, so
  that part is in scope by default; a custom "forgot password" screen is
  not).

## Decision 1: backend hosting — Render free Web Service

Supabase provides Postgres + Auth + Storage + Edge Functions (Deno/TypeScript)
— it does not run arbitrary Python/FastAPI applications. `CLAUDE.md`'s
original "Backend/DB → Supabase" roadmap line undersold this: Supabase
only ever covers the DB/Auth half. The backend (FastAPI) needs a separate
host.

**Decision: Render's free Web Service tier**, building from the existing
`backend/Dockerfile`. No card required, genuinely free (750 hrs/month),
supports Docker directly. Cold starts after ~15 minutes of inactivity
(~30s wake-up) — acceptable for a portfolio project, not acceptable for
a paid product, which this isn't. This is a different Render product
than the Postgres tier already ruled out in `CLAUDE.md` (that one expires
after 30 days; the Web Service tier has no such expiry).

Rejected: Google Cloud Run (generous free tier, but requires a card on
file even though usage stays free — breaks the project's card-free
hosting pattern); rewriting the backend as Supabase Edge Functions
(bigger rewrite, loses the Python backend as a portfolio piece
demonstrating the data pipeline work, which is this project's whole
point per `CLAUDE.md`'s "What this is" section).

## Decision 2: auth required before onboarding

`DESIGN.md`'s screen flow (`Landing → Log in/sign up → Set goal (onboarding)
→ Dashboard`) puts login before goal-setting. Sprint 3 built onboarding
as the first stop with no auth at all. Sprint 4 makes login a hard
prerequisite: an unauthenticated visit to `/onboarding` or any `(hub)`
route (`/`, `/browse`, `/course/[id]`, `/profile`) redirects to `/login`.

This is chosen over keeping anonymous onboarding with optional
account-linking specifically because it avoids a whole category of
complexity: merging a `localStorage` path/progress into a freshly-created
account, deciding what happens on conflict, etc. Trading that complexity
away is worth the (deliberate) loss of the "try before you sign up" UX —
acceptable for a portfolio project where account creation is free and
frictionless (no payment info, no email verification gate before first
use, if the default Supabase flow doesn't require verified email to sign
in — confirm this during setup and disable a mandatory verification gate
if it's on by default, so signup stays frictionless).

## Decision 3: auth methods — email/password only

`DESIGN.md`'s login screen mockup includes "Continue with Google"
alongside email/password. Google OAuth is deferred (Non-goals) —
building it now means configuring a separate Google Cloud OAuth client
(distinct from the existing YouTube Data API key) and wiring an OAuth
redirect flow through Supabase Auth, extra setup surface for a feature
that can be added later without a data model change. The login/signup
screens still get built to `DESIGN.md`'s visual spec; the Google button
either gets deferred visually too (simplest: don't render it yet) or
rendered disabled — implementation detail for the plan, not a spec-level
decision.

## Decision 4: local dev — Supabase CLI local stack replaces plain Postgres

Supabase Auth cannot run against the existing `docker-compose.yml`'s
vanilla `postgres:16` container — Auth needs Supabase's own schema,
services, and Postgres extensions. The Supabase CLI provides `supabase
start`, a Docker-based local stack (Postgres + Auth (GoTrue) + Studio +
more) that mirrors the hosted environment closely enough for real login
to work in local dev without any network dependency or hosted-project
quota usage.

**Consequences for existing dev tooling** (built in the post-Sprint-3
tooling pass, see `CLAUDE.md`'s "Dev/prod tooling" section):
- `docker-compose.yml` (currently just Postgres) is replaced by the
  Supabase CLI stack for dev. `start-sp.bat`/`stop-sp.bat` change from
  `docker compose up -d`/`stop` to `supabase start`/`supabase stop`.
- Migrations move from `migrations/*.sql` to the Supabase CLI's expected
  `supabase/migrations/<timestamp>_<name>.sql` layout. The existing SQL
  is largely compatible; this is a relocation/rename, not a rewrite.
  Applied via `supabase db reset` (local) rather than manual `psql`.
- `docker-compose.prod.yml` (the local production-build smoke test built
  in the tooling pass) has the same problem — its own plain Postgres
  container can't run Supabase Auth either. Rather than stand up a
  third separate database definition, the prod smoke test's backend
  points at the same Supabase CLI local stack instead of its own `db`
  service. `docker-compose.prod.yml`'s `db` service and
  `skillpath_pgdata_prod` volume are removed; `start-sp-prod.bat` gains
  a dependency on `supabase start` having already been run (or the
  script runs it as a first step).
- `backend/db.py`'s `get_connection()` pattern (`DATABASE_URL` from
  `.env`) is unchanged — only the URL value changes, to the Supabase
  CLI stack's local Postgres connection string instead of port 5432's
  vanilla container.

## Decision 5: database schema — `user_goals` and `completed_courses`

`CLAUDE.md`'s original placeholder for later sprints named `users`,
`user_goals`, `learning_paths`, `path_steps`. Supabase Auth already
provides `auth.users` — a separate `public.users` table would duplicate
it for no reason (YAGNI). The other three collapse into two tables that
directly mirror what `StoredPath` did client-side in Sprint 3:

```sql
CREATE TABLE user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES goals(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE TABLE completed_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, course_id)
);
```

`UNIQUE (user_id)` on `user_goals` means one active goal per user at a
time — matches Sprint 3's `StoredPath` model (one path in `localStorage`
at once) and the existing "Change goal" flow (changing goals
replaces the row rather than accumulating history). If per-user goal
history ever matters (e.g. "goals you've completed in the past"), that's
a schema change for a later sprint, not this one.

## Decision 6: backend auth verification

New `backend/auth.py` — a FastAPI dependency that reads the
`Authorization: Bearer <token>` header, verifies the JWT Supabase issued
(against the project's JWT signing key — confirm during setup whether
the created Supabase project uses the legacy shared HS256 secret or the
newer asymmetric JWKS-based signing, since Supabase has been migrating
projects toward the latter; the plan should verify against whichever the
actual project uses rather than assuming), and returns the authenticated
user's id (the JWT's `sub` claim) or raises 401. This dependency gates
every endpoint that reads or writes per-user data.

**Reshaped/new endpoints:**
- `POST /paths` changes from purely computing and returning a path to
  also persisting the choice into `user_goals` (upserting, replacing any
  existing row per Decision 5's `UNIQUE (user_id)`) for the now-required
  authenticated caller.
- `GET /me/path` — fetch the calling user's current goal + full path
  (steps, courses, completion state) in one response, replacing what
  `useLocalPath`'s `path` value provided from `localStorage`.
- `POST /me/progress` — toggle a course's completion for the calling
  user (insert/delete a row in `completed_courses`), replacing
  `toggleCourseComplete`.
- `DELETE /me/path` (or reuse `POST /paths` with upsert semantics per
  above — implementation detail for the plan) — replacing `clearPath`
  for the "Change goal" flow.

`GET /courses` and `GET /courses/{id}` (Sprint 3) are unaffected — they
serve public course data, not per-user state.

## Decision 7: frontend auth flow and route protection

New `/login` and `/signup` screens built with `supabase-js`
(`supabase.auth.signUp`/`signInWithPassword`), following `DESIGN.md`'s
login screen spec (email, password, forgot-password link — link only,
no working flow behind it per Non-goals — primary button, divider,
sign-up link; Google button deferred per Decision 3).

Route protection: every `(hub)` route and `/onboarding` checks for a
valid Supabase session (via `supabase.auth.getSession()`/`onAuthStateChange`)
and redirects to `/login` if absent — implementation detail for the plan
whether this is a shared layout-level check or per-page, but it must
cover all of `/onboarding`, `/`, `/browse`, `/course/[id]`, `/profile`.

`useLocalPath` (Sprint 3) is replaced by a new hook that calls the
`/me/*` endpoints instead of reading/writing `localStorage`, attaching
the current Supabase session's access token as the `Authorization`
header on every call. The hook's consumer-facing shape (what it returns:
something like `path`, `toggleCourseComplete`, `isCourseComplete`,
`clearPath`, `isLoaded`) should stay as close to Sprint 3's shape as
reasonable, since every screen already consumes that interface — this
minimizes churn in the screens themselves, which are explicitly not
being redesigned (Non-goals).

## Decision 8: deployment

- **Frontend → Vercel**: connect the GitHub repo, root directory
  `frontend/`. Environment variables: `NEXT_PUBLIC_API_BASE_URL` (the
  deployed Render backend's URL), `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Backend → Render free Web Service** (Decision 1), built from
  `backend/Dockerfile`. Environment variables: `DATABASE_URL` (the
  hosted Supabase Postgres connection string), `CORS_ORIGINS` (the
  deployed Vercel domain), the Supabase JWT signing key/secret needed
  for Decision 6's verification.
- **Supabase**: hosted Postgres + Auth. Migrations applied via
  `supabase db push` (pushes local `supabase/migrations/` to the linked
  hosted project) or, if that's not working smoothly, manually through
  the Supabase dashboard's SQL editor as a fallback.
- Account creation (Supabase project, Render account, Vercel account)
  and copying the resulting keys/URLs into place is user setup work,
  same pattern as Sprint 1's YouTube API key — the plan should include
  a clear step-by-step walkthrough for this (the `wizard` skill is a
  good fit for generating an interactive script for this part).

## Build order

Mirrors Sprint 3's pattern (infra → core loop → rest):

1. Account setup: Supabase project, Render account, Vercel account
   created; Supabase CLI installed locally.
2. Local dev environment: Supabase CLI stack replacing
   `docker-compose.yml`; migrations relocated to `supabase/migrations/`;
   `user_goals`/`completed_courses` schema added.
3. Backend: `backend/auth.py` verification dependency; reshaped
   `POST /paths`; new `GET /me/path`, `POST /me/progress`,
   goal-change endpoint.
4. Frontend: `supabase-js` wired in; `/login` and `/signup` screens;
   route protection across `/onboarding` and all `(hub)` routes.
5. Frontend: new server-backed hook replacing `useLocalPath`; every
   screen that consumed the old hook updated to the new one.
6. Update `docker-compose.prod.yml`/`start-sp-prod.bat` to depend on the
   Supabase CLI stack instead of their own Postgres service.
7. Deploy: Supabase migrations pushed to the hosted project, backend to
   Render, frontend to Vercel; end-to-end smoke test against the real
   deployed stack.

## Open items carried into the implementation plan

- Exact shape of `GET /me/path`'s response schema (mirroring
  Sprint 3's `PathResponse`/`StoredPath` shapes as closely as sensible).
- Whether Supabase's default email-confirmation-required-before-login
  setting needs to be disabled for a frictionless signup (Decision 2's
  parenthetical) — verify against the actual created project's default
  during setup, not assumed here.
- Whether the created Supabase project signs JWTs with a legacy shared
  secret or the newer asymmetric JWKS scheme (Decision 6) — verify
  against the actual project, implement verification accordingly.
- Exact new route-protection mechanism (middleware vs. layout-level
  check vs. per-page) — implementation detail, not a spec-level decision.
