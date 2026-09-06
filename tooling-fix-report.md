# Tooling audit fixes — report

Scope: `package.json` (root), `docker-compose.yml`, `docker-compose.prod.yml`,
`backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore` (root),
`frontend/.dockerignore`, `start-sp.bat`, `stop-sp.bat`, `start-sp-prod.bat`,
`stop-sp-prod.bat`. `frontend/Dockerfile` and `docker-compose.yml` (dev) needed
no changes — included in the read-first pass, no edits required.

## Fix 1 — `.dockerignore` path-anchoring gaps

- Root `.dockerignore`: `__pycache__/` → `**/__pycache__/`, `*.pyc` →
  `**/*.pyc`, `.env` → `**/.env*` (broadened to also catch `.env.local` etc.,
  matches root-level `.env` too since `**` matches zero segments).
- Confirmed root `.env.example` exists (161 bytes) but the backend image
  doesn't need it at build or run time (it reads config via
  `os.environ`/`python-dotenv` from actual env vars, not a bundled example
  file) — no negation needed, plain broad exclusion is correct.
- `frontend/.dockerignore`: `.env*.local` → `.env` + `.env*`, kept
  `!.env.local.example` negation so that fixture file still ships into the
  build stage.

## Fix 2 — Backend Docker image Python version

- Dev venv (`venv/Scripts/python.exe --version`) reports **Python 3.14.2**.
- `backend/Dockerfile` was pinned to `python:3.13-slim`.
- Verified `python:3.14-slim` exists on Docker Hub via `docker pull
  python:3.14-slim` — pulled successfully (digest
  `sha256:cad9a2c8...`). Updated the Dockerfile's `FROM` line to
  `python:3.14-slim`, an exact minor-version match, no discrepancy to note.
- Confirmed via the live build (see Verification) that `pip install -r
  requirements.txt` succeeds cleanly under 3.14 — all packages (psycopg,
  fastapi, uvicorn, pytest, etc.) had compatible wheels.

## Fix 3 — Dev/prod port collision

- `docker-compose.prod.yml`: backend port mapping `8000:8000` →
  `"8001:8000"`; frontend `3000:3000` → `"3001:3000"` (container-internal
  ports unchanged).
- Frontend build arg `NEXT_PUBLIC_API_BASE_URL` updated to
  `http://localhost:8001`.
- Read `backend/main.py`: confirmed
  `CORS_ORIGINS` default is already
  `"http://localhost:3000,http://localhost:3001"` (a prior agent's fix) —
  no compose-level `CORS_ORIGINS` override needed.
- All three prod services' `restart: unless-stopped` → `restart: "no"`.

## Fix 4 — Prod DB migrations only apply once

- `start-sp-prod.bat` now runs `docker compose -f docker-compose.prod.yml
  down -v` before `up -d --build`, so the named volume
  (`skillpath_pgdata_prod`) is destroyed and recreated fresh every run,
  guaranteeing `docker-entrypoint-initdb.d` (the mounted `./migrations`)
  actually re-executes.

## Fix 5 — `.bat` script safety net

All four scripts (`start-sp.bat`, `stop-sp.bat`, `start-sp-prod.bat`,
`stop-sp-prod.bat`) now follow the pattern:
```bat
@echo off
cd /d "%~dp0"
<existing docker compose command(s)>
if errorlevel 1 pause
exit /b %errorlevel%
```
`start-sp-prod.bat`'s middle section is the two-line `down -v` + `up -d
--build` sequence from Fix 4.

## Fix 6 — `npm run dev:full` doesn't start the database

- Root `package.json`'s `dev:full` script changed from:
  `"concurrently -n backend,frontend -c blue,green \"npm run dev:backend\" \"npm run dev:frontend\""`
  to:
  `"docker compose up -d && concurrently -n backend,frontend -c blue,green \"npm run dev:backend\" \"npm run dev:frontend\""`

## Fix 7 — Prod compose credential triplication

- `db` service: `POSTGRES_PASSWORD: skillpath` →
  `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-skillpath}`.
- `backend` service: `DATABASE_URL:
  postgresql://skillpath:skillpath@db:5432/skillpath` →
  `postgresql://skillpath:${POSTGRES_PASSWORD:-skillpath}@db:5432/skillpath`.
- Password now single-sourced via one env var with a local-friendly default;
  overridable via a gitignored `.env` next to the compose file, per Compose's
  automatic `.env` loading.

## Verification

### `docker compose config` (dev)
Ran clean. Resolved service `db` on port `5432`, volume
`skillpath_pgdata`, `restart: unless-stopped` (dev stack intentionally
untouched by this fix pass).

### `docker compose -f docker-compose.prod.yml config` (prod)
Ran clean, no unexpected warnings (no `.env` file present locally, so
`POSTGRES_PASSWORD` fell back to its default `skillpath` in both the `db`
and `backend` service blocks — consistent, no drift). Confirmed in the
resolved output:
- `backend` → `published: "8001"`, target `8000`, `restart: 'no'`
- `frontend` → `published: "3001"`, target `3000`, `restart: 'no'`,
  build arg `NEXT_PUBLIC_API_BASE_URL: http://localhost:8001`
- `db` → `published: "5433"`, `restart: 'no'`, password interpolated
  consistently in both `db.environment.POSTGRES_PASSWORD` and
  `backend.environment.DATABASE_URL`

### Live prod-stack smoke test (Docker Desktop was available)

Docker Desktop was running (Docker Desktop 4.85.0, engine 29.6.2). Found and
cleaned up stale `Exited` prod containers left over from a prior manual run
before starting my own test.

1. `docker compose -f docker-compose.prod.yml down -v` — tore down
   pre-existing stopped prod containers/volume/network cleanly.
2. `docker compose -f docker-compose.prod.yml up -d --build` — backend
   image built on `python:3.14-slim` (pip install succeeded, ~17s), frontend
   image built on `node:22-slim` (Next.js 16.3.4 build succeeded, ~21s). All
   three containers (`skillpath_db_prod`, `skillpath_backend_prod`,
   `skillpath_frontend_prod`) started; DB reported healthy.
3. `docker ps` confirmed port mappings: `8001->8000` (backend),
   `3001->3000` (frontend), `5433->5432` (db) — alongside dev's
   `skillpath_db` still running untouched on `5432`.
4. `curl -s -X POST http://localhost:8001/paths -H "Content-Type:
   application/json" -d '{"goal_slug":"data-analyst"}'` returned:
   ```json
   {"goal":{"name":"Data Analyst","slug":"data-analyst"},"steps":[{"skill":{"name":"SQL","slug":"sql"},"courses":[]},{"skill":{"name":"Python","slug":"python"},"courses":[]},{"skill":{"name":"Statistics","slug":"statistics"},"courses":[]},{"skill":{"name":"Data Visualization","slug":"data-visualization"},"courses":[]}]}
   ```
   Valid response confirming migrations applied (goal + skills seeded from
   `002_goals.sql`) and the backend/DB wiring on the new ports works
   end-to-end. `courses: []` for every step is expected — this prod DB only
   ran migrations (schema + seed data), it was never populated by the
   ingestion script, so there's no course data to join against.
5. `docker compose -f docker-compose.prod.yml down -v` — cleaned up the
   prod stack, volume, and network after testing.
6. `docker ps` confirmed only `skillpath_db` (dev) remains running on
   `5432`, healthy, untouched by the prod-stack testing.

## Concerns

None outstanding. All 7 fixes implemented, both compose files validate,
and the live smoke test exercised the actual failure mode Fix 3/4 were
meant to close (fresh migrations, non-colliding ports) end-to-end
successfully.

One minor note for the user: `python:3.14-slim` is a very recent Python
minor version — if the dev venv is later rebuilt against a different
Python (e.g. a future 3.14.x patch bump or someone recreating the venv
under 3.13 for tooling-compatibility reasons), this Dockerfile pin should
be re-checked against `venv/Scripts/python.exe --version` again, since
nothing enforces that link automatically.

## Addendum — reviewer follow-up (2 Important findings)

A reviewer pass on the fixes above found 2 Important issues, both fixed
in a follow-up commit.

### Finding 1: `frontend/.dockerignore` still not anchored "at any depth"

The first fix changed the patterns to `.env` / `.env*` /
`!.env.local.example`, but these still lacked the `**/` prefix — they only
matched at the frontend build context root, not at any depth, which was
the exact anchoring gap the audit asked to close (and inconsistent with
the root `.dockerignore`'s `**/.env*`).

**Fix applied:** collapsed to two lines —
```
**/.env*
!**/.env.local.example
```
(the earlier separate `.env` line was also redundant, since `.env*`
already matches the bare `.env` filename — glob `*` matches zero or more
characters). Verified the fixture file actually lives at
`frontend/.env.local.example` (context root, confirmed via `find`), so
the negation, now also `**/`-prefixed, still matches and correctly
un-excludes it after the broadened exclusion.

### Finding 2: `start-sp-prod.bat` lost error visibility between `down -v` and `up -d --build`

The two `docker compose` calls ran as independent lines with no chaining
or intermediate errorlevel check, so only the last command's (`up -d
--build`) exit code reached the final `if errorlevel 1 pause` / `exit /b
%errorlevel%`. A failed `down -v` (e.g. a lingering container handle or
still-attached volume) could be followed by a successful `up -d --build`
against the stale volume, silently reproducing the exact "migrations
only apply once" failure mode Fix 4 exists to eliminate.

**Fix applied:** inserted an explicit errorlevel check immediately after
`down -v`:
```bat
docker compose -f docker-compose.prod.yml down -v
if errorlevel 1 (
    pause
    exit /b %errorlevel%
)
docker compose -f docker-compose.prod.yml up -d --build
if errorlevel 1 pause
exit /b %errorlevel%
```
Reasoned through the failure path rather than forcing a real Docker
failure (not practical to reproduce safely): cmd.exe expands `%errorlevel%`
inside a parenthesized block once, at the point the block is entered —
i.e., using the errorlevel set by `down -v`, before `pause` runs. Since
`pause` does not alter errorlevel in normal (non-Ctrl+C) use, `exit /b
%errorlevel%` inside the block correctly propagates `down -v`'s failure
code and the script exits before `up -d --build` is ever reached. On a
successful `down -v` (errorlevel 0), the block is skipped and the script
proceeds to `up -d --build` as before, with its own existing errorlevel
check at the bottom.

### Verification (addendum)

- Re-read `frontend/.dockerignore` and `start-sp-prod.bat` after editing
  to confirm exact contents (shown above).
- `docker compose -f docker-compose.prod.yml config` re-run: output
  unchanged from the prior verification pass (same ports, `restart: 'no'`,
  password interpolation) — confirms nothing else broke.
- `docker ps` re-confirmed only `skillpath_db` (dev) running on `5432`,
  untouched.
- Did not force a live `down -v` failure (no safe/practical way to induce
  one — e.g. holding a container handle open — without risking an
  unrelated container); verified the batch logic by tracing the
  errorlevel-expansion semantics instead, as noted above.

No further concerns from this addendum.
