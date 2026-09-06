# Sprint 4 Auth, Data Migration, and Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real Supabase Auth (email/password), migrate progress/path
state from `localStorage` to server-persisted tables scoped per user, and
prepare the app to deploy (Vercel + Render + hosted Supabase).

**Architecture:** Supabase Auth issues JWTs; the frontend talks to Supabase
directly via `supabase-js` for signup/login. FastAPI verifies the JWT on
every protected request (extracting the user id from its `sub` claim) via
a new `backend/auth.py` dependency, rather than reimplementing auth.
Two new Postgres tables (`user_goals`, `completed_courses`), both
referencing Supabase's own `auth.users`, replace the `StoredPath`
`localStorage` shape from Sprint 3. Local dev runs against the Supabase
CLI's local emulator stack (Postgres + Auth together) instead of a plain
Postgres container, since Auth needs Supabase's own schema/services.

**Tech Stack:** FastAPI + psycopg (unchanged) + PyJWT (new, for JWT
verification) on the backend. Next.js + `@supabase/supabase-js` (new) on
the frontend. Supabase CLI for local dev; Supabase-hosted Postgres+Auth,
Render (backend), Vercel (frontend) for deploy.

**Spec:** `docs/superpowers/specs/2026-09-06-sprint4-auth-deploy-design.md`

**Precondition:** `scripts/setup-sprint4-dev.sh` must already have been
run by the user before starting this plan — it installs the Supabase CLI
access path, creates the hosted Supabase project, runs `supabase init`
and `supabase start`, and writes `DATABASE_URL`, `SUPABASE_JWT_SECRET`,
and the frontend's `NEXT_PUBLIC_SUPABASE_URL`/`NEXT_PUBLIC_SUPABASE_ANON_KEY`
to `.env`/`frontend/.env.local`. If `supabase/config.toml` doesn't exist
yet, stop and tell the user to run that script first.

## Global Constraints

- Login is required before `/onboarding` and every `(hub)` route
  (`/`, `/browse`, `/course/[id]`, `/profile`) — an unauthenticated visit
  redirects to `/login`.
- Email/password auth only this sprint — no Google OAuth, no custom
  password-reset or email-verification UI.
- `user_goals` has `UNIQUE (user_id)` — one active goal per user at a
  time, matching Sprint 3's one-path-at-a-time model.
- `completed_courses` has `UNIQUE (user_id, course_id)`.
- Migrations live in `supabase/migrations/<timestamp>_<name>.sql`,
  applied locally via `npx supabase db reset` — not the old
  `migrations/*.sql` + manual `psql` workflow.
- JWT verification uses HS256 with `SUPABASE_JWT_SECRET` (the local
  Supabase CLI stack's shared secret, already in `.env` per the
  precondition). If the hosted project turns out to sign JWTs
  asymmetrically instead, that's a pre-deploy follow-up, not something
  to guess at now — local dev's CLI stack uses HS256 by default.
- No visual/UX redesign of any existing screen — only swap each screen's
  data source from `localStorage`/`useLocalPath` to the server/
  `useServerPath`. Copy, layout, and Tailwind classes stay as they are
  except where a task explicitly says otherwise.
- `useServerPath`'s consumer-facing shape mirrors `useLocalPath`'s
  (`path`, `isLoaded`, `toggleCourseComplete`, `isCourseComplete`,
  `clearPath`) plus a new `refresh` function, so existing screens need
  minimal changes beyond the import.
- Local Docker Postgres is gone this sprint — do not use `docker compose`
  for dev anymore; use `npx supabase start`/`stop`/`status`.

---

## Task 1: Relocate migrations to Supabase CLI layout; retire dev Postgres compose

**Files:**
- Create: `supabase/migrations/20260101000000_initial_schema.sql`
  (copy of `migrations/001_initial_schema.sql`, unchanged content)
- Create: `supabase/migrations/20260101000001_goals.sql`
  (copy of `migrations/002_goals.sql`, unchanged content)
- Delete: `migrations/001_initial_schema.sql`, `migrations/002_goals.sql`,
  the now-empty `migrations/` directory
- Delete: `docker-compose.yml`
- Modify: `start-sp.bat`, `stop-sp.bat`, `package.json`
- Modify: `.gitignore`

**Interfaces:**
- Produces: a working `npx supabase start`/`npx supabase stop` dev
  workflow that later tasks (and the existing `pytest`/`npm run dev:full`
  commands) depend on for a running Postgres+Auth stack.

- [ ] **Step 1: Copy the two existing migrations into `supabase/migrations/` with CLI-ordered filenames**

Read `migrations/001_initial_schema.sql` and `migrations/002_goals.sql` in
full, then create these two files with identical content (only the
filename changes):

`supabase/migrations/20260101000000_initial_schema.sql` — exact copy of
`migrations/001_initial_schema.sql`.

`supabase/migrations/20260101000001_goals.sql` — exact copy of
`migrations/002_goals.sql`.

- [ ] **Step 2: Delete the old `migrations/` directory**

```bash
git rm migrations/001_initial_schema.sql migrations/002_goals.sql
rmdir migrations
```

- [ ] **Step 3: Delete the dev Postgres-only compose file**

```bash
git rm docker-compose.yml
```

- [ ] **Step 4: Update `start-sp.bat` to use the Supabase CLI**

Replace the full content of `start-sp.bat` with:

```bat
@echo off
cd /d "%~dp0"
npx supabase start
if errorlevel 1 pause
exit /b %errorlevel%
```

- [ ] **Step 5: Update `stop-sp.bat` to use the Supabase CLI**

Replace the full content of `stop-sp.bat` with:

```bat
@echo off
cd /d "%~dp0"
npx supabase stop
if errorlevel 1 pause
exit /b %errorlevel%
```

- [ ] **Step 6: Update `package.json`'s `dev:full` script**

Open `package.json` and change the `dev:full` script value from starting
`docker compose` to starting the Supabase CLI stack. The rest of the
file (`dev:backend`, `dev:frontend`, `devDependencies`) stays as-is:

```json
"dev:full": "npx supabase start && concurrently -n backend,frontend -c blue,green \"npm run dev:backend\" \"npm run dev:frontend\""
```

- [ ] **Step 7: Add Supabase CLI artifacts to `.gitignore`**

Add this line to `.gitignore` (anywhere among the existing entries):

```
supabase/.temp
```

- [ ] **Step 8: Verify the new dev stack starts and reset the DB onto it**

Run: `npx supabase start` (if not already running from the setup
wizard — it's idempotent, safe to re-run) then
`npx supabase db reset` to apply the two relocated migrations onto the
local stack.
Expected: `supabase db reset` reports both migrations applied with no
errors, and `npx supabase status` shows the API/DB/Studio URLs.

- [ ] **Step 9: Commit**

```bash
git add supabase/migrations/ start-sp.bat stop-sp.bat package.json .gitignore
git commit -m "chore: move migrations to Supabase CLI layout, retire dev Postgres compose"
```

---

## Task 2: Add `user_goals` and `completed_courses` schema

**Files:**
- Create: `supabase/migrations/20260101000002_user_progress.sql`

**Interfaces:**
- Produces: `user_goals` table (`id`, `user_id` FK → `auth.users(id)`,
  `goal_id` FK → `goals(id)`, `created_at`, `UNIQUE(user_id)`) and
  `completed_courses` table (`id`, `user_id` FK → `auth.users(id)`,
  `course_id` FK → `courses(id)`, `completed_at`,
  `UNIQUE(user_id, course_id)`) — consumed by Task 4's query functions.

- [ ] **Step 1: Create the migration file**

```sql
-- Sprint 4 schema: user_goals, completed_courses
-- References Supabase Auth's auth.users table directly rather than
-- duplicating it as a separate public.users table.

CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES goals(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS completed_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id),
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_user_goals_user ON user_goals(user_id);
CREATE INDEX IF NOT EXISTS idx_completed_courses_user ON completed_courses(user_id);
```

- [ ] **Step 2: Apply and verify**

Run: `npx supabase db reset`
Expected: all three migrations (initial schema, goals, user_progress)
apply cleanly with no errors.

Run a quick verification query:
```bash
venv/Scripts/python.exe -c "
import psycopg, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT tablename FROM pg_tables WHERE tablename IN ('user_goals','completed_courses')\")
print(cur.fetchall())
"
```
Expected: `[('user_goals',), ('completed_courses',)]` (order may vary).

- [ ] **Step 3: Commit**

```bash
git add supabase/migrations/20260101000002_user_progress.sql
git commit -m "feat: add user_goals and completed_courses schema"
```

---

## Task 3: JWT verification dependency + test auth helpers

**Files:**
- Modify: `requirements.txt`
- Create: `backend/auth.py`
- Create: `tests/auth_helpers.py`
- Create: `tests/conftest.py`
- Create: `tests/test_auth.py`

**Interfaces:**
- Produces: `backend.auth.get_current_user_id(authorization: str | None
  = Header(default=None)) -> str` — a FastAPI dependency raising
  `HTTPException(401)` on a missing/malformed/invalid/expired token,
  returning the JWT's `sub` claim (the Supabase user id) otherwise. Used
  by Task 5 and Task 6's endpoints via `Depends(get_current_user_id)`.
- Produces: `tests.auth_helpers.create_test_user(email: str, password:
  str = "testpassword123") -> str`, `delete_test_user(user_id: str) ->
  None`, `make_test_jwt(user_id: str) -> str` — used by this task's own
  tests and by Tasks 5/6's tests via the `tests/conftest.py` fixtures.
- Produces: pytest fixtures `test_user_id` (session-scoped, creates one
  real Supabase Auth user via the admin API, deletes it after the test
  session) and `auth_headers` (function-scoped, `{"Authorization":
  "Bearer <token>"}` for that user) — consumed by every later backend
  test that needs an authenticated request.

- [ ] **Step 1: Add PyJWT to `requirements.txt`**

Append this line to `requirements.txt`:
```
PyJWT==2.10.1
```

Run: `venv/Scripts/python.exe -m pip install -r requirements.txt -q`

- [ ] **Step 2: Create `backend/auth.py`**

```python
import os
import time

import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    load_dotenv()
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="missing or invalid authorization header"
        )
    token = authorization.removeprefix("Bearer ")

    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. Run scripts/setup-sprint4-dev.sh "
            "and add it to your .env file."
        )

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid or expired token")

    return payload["sub"]
```

- [ ] **Step 3: Create `tests/auth_helpers.py`**

```python
import os
import time

import httpx
import jwt
from dotenv import load_dotenv


def create_test_user(email: str, password: str = "testpassword123") -> str:
    load_dotenv()
    base_url = os.environ["SUPABASE_LOCAL_URL"]
    service_role_key = os.environ["SUPABASE_LOCAL_SERVICE_ROLE_KEY"]
    response = httpx.post(
        f"{base_url}/auth/v1/admin/users",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
        json={"email": email, "password": password, "email_confirm": True},
    )
    response.raise_for_status()
    return response.json()["id"]


def delete_test_user(user_id: str) -> None:
    load_dotenv()
    base_url = os.environ["SUPABASE_LOCAL_URL"]
    service_role_key = os.environ["SUPABASE_LOCAL_SERVICE_ROLE_KEY"]
    httpx.delete(
        f"{base_url}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
    )


def make_test_jwt(user_id: str) -> str:
    load_dotenv()
    secret = os.environ["SUPABASE_JWT_SECRET"]
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
import pytest

from tests.auth_helpers import create_test_user, delete_test_user, make_test_jwt


@pytest.fixture(scope="session")
def test_user_id():
    user_id = create_test_user("sprint4-test-user@example.com")
    yield user_id
    delete_test_user(user_id)


@pytest.fixture
def auth_headers(test_user_id):
    token = make_test_jwt(test_user_id)
    return {"Authorization": f"Bearer {token}"}
```

(This is a new file distinct from the empty root `conftest.py` — the
root one exists purely so plain `pytest` resolves import paths; this one
holds real fixtures scoped to `tests/`.)

- [ ] **Step 5: Write `tests/test_auth.py`**

```python
import os
import time

import jwt
import pytest
from fastapi import HTTPException

from backend.auth import get_current_user_id


def test_get_current_user_id_returns_sub_for_valid_token(auth_headers, test_user_id):
    token = auth_headers["Authorization"].removeprefix("Bearer ")
    user_id = get_current_user_id(authorization=f"Bearer {token}")
    assert user_id == test_user_id


def test_get_current_user_id_rejects_missing_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=None)
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_malformed_header():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization="NotBearer sometoken")
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_invalid_signature():
    bad_token = jwt.encode(
        {"sub": "00000000-0000-0000-0000-000000000000", "aud": "authenticated"},
        "wrong-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {bad_token}")
    assert exc_info.value.status_code == 401


def test_get_current_user_id_rejects_expired_token(test_user_id):
    secret = os.environ["SUPABASE_JWT_SECRET"]
    expired_token = jwt.encode(
        {
            "sub": test_user_id,
            "aud": "authenticated",
            "exp": int(time.time()) - 60,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(authorization=f"Bearer {expired_token}")
    assert exc_info.value.status_code == 401
```

- [ ] **Step 6: Run the new tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_auth.py -v`
Expected: all 5 tests PASS. (This makes a real call to the local
Supabase Auth admin API to create a test user — `npx supabase start`
must be running.)

- [ ] **Step 7: Run the full suite to confirm no regressions**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all prior tests (23) plus the 5 new ones PASS (28 total).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt backend/auth.py tests/auth_helpers.py tests/conftest.py tests/test_auth.py
git commit -m "feat: add JWT verification dependency and test auth helpers"
```

---

## Task 4: User-progress query functions + shared `PathStep` schema

**Files:**
- Modify: `backend/queries.py`
- Modify: `backend/schemas.py`

**Interfaces:**
- Produces: `backend.queries.upsert_user_goal(conn, user_id: str,
  goal_id: str) -> None`, `get_user_goal(conn, user_id: str) -> dict |
  None` (dict has `id`, `name`, `slug`), `delete_user_goal(conn, user_id:
  str) -> None`, `get_completed_course_ids(conn, user_id: str) ->
  list[str]`, `toggle_completed_course(conn, user_id: str, course_id:
  str) -> bool` (returns the new completion state) — consumed by Task 5
  and Task 6.
- Produces: `backend.schemas.PathStep` (`skill: SkillOut`, `courses:
  list[CourseOut]`) — moved here from `backend/routers/paths.py` so
  Task 6's new router can reuse it without duplicating the class.

- [ ] **Step 1: Move `PathStep` into `backend/schemas.py`**

Add to the end of `backend/schemas.py`:

```python
class PathStep(BaseModel):
    skill: SkillOut
    courses: list[CourseOut]
```

- [ ] **Step 2: Remove `PathStep`'s local definition from `backend/routers/paths.py`**

In `backend/routers/paths.py`, remove the local `class PathStep(BaseModel):
...` definition, and add `PathStep` to the existing schemas import:

```python
from backend.schemas import CourseOut, GoalOut, PathStep, SkillOut
```

(The `PathRequest` and `PathResponse` classes stay as they are — only
`PathStep` moves out.)

- [ ] **Step 3: Verify existing tests still pass after the schema move**

Run: `venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: all 4 tests still PASS — this is a pure refactor, no behavior
change yet.

- [ ] **Step 4: Add the five query functions to `backend/queries.py`**

Append to `backend/queries.py`:

```python
def upsert_user_goal(conn: psycopg.Connection, user_id: str, goal_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_goals (user_id, goal_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET goal_id = EXCLUDED.goal_id, created_at = now()
            """,
            (user_id, goal_id),
        )
        conn.commit()


def get_user_goal(conn: psycopg.Connection, user_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT g.id, g.name, g.slug
            FROM user_goals ug
            JOIN goals g ON g.id = ug.goal_id
            WHERE ug.user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {"id": str(row[0]), "name": row[1], "slug": row[2]}


def delete_user_goal(conn: psycopg.Connection, user_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM user_goals WHERE user_id = %s", (user_id,))
        conn.commit()


def get_completed_course_ids(conn: psycopg.Connection, user_id: str) -> list[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT course_id FROM completed_courses WHERE user_id = %s", (user_id,)
        )
        return [str(r[0]) for r in cur.fetchall()]


def toggle_completed_course(conn: psycopg.Connection, user_id: str, course_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM completed_courses WHERE user_id = %s AND course_id = %s",
            (user_id, course_id),
        )
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(
                "DELETE FROM completed_courses WHERE user_id = %s AND course_id = %s",
                (user_id, course_id),
            )
            conn.commit()
            return False
        else:
            cur.execute(
                "INSERT INTO completed_courses (user_id, course_id) VALUES (%s, %s)",
                (user_id, course_id),
            )
            conn.commit()
            return True
```

Note the explicit `conn.commit()` after each write — `backend/db.py`'s
connections are not autocommit (unlike `scripts/ingest_youtube.py`'s),
so writes here must commit explicitly or they're silently rolled back
when the router's `finally: conn.close()` runs.

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all 28 tests still PASS (these new functions aren't wired to
any endpoint yet, so nothing new to test here — Tasks 5/6 add the tests
that exercise them).

- [ ] **Step 6: Commit**

```bash
git add backend/queries.py backend/schemas.py backend/routers/paths.py
git commit -m "feat: add user-progress query functions, extract shared PathStep schema"
```

---

## Task 5: Require auth on `POST /paths`; persist the chosen goal

**Files:**
- Modify: `backend/routers/paths.py`
- Modify: `tests/test_paths.py`
- Modify: `tests/test_cors.py`

**Interfaces:**
- Consumes: `backend.auth.get_current_user_id` (Task 3);
  `backend.queries.upsert_user_goal` (Task 4).
- Produces: `POST /paths` now requires a valid `Authorization: Bearer
  <token>` header (401 otherwise) and persists the resolved goal into
  `user_goals` for the calling user, in addition to its existing
  response shape (`PathResponse`, unchanged).

- [ ] **Step 1: Update the failing/passing tests first (TDD-in-reverse:
  encode the new required behavior, then implement it)**

Replace the full content of `tests/test_paths.py`:

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_create_path_returns_ordered_steps(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["goal"] == {"name": "Data Analyst", "slug": "data-analyst"}
    skill_slugs = [step["skill"]["slug"] for step in body["steps"]]
    assert skill_slugs == ["sql", "python", "statistics", "data-visualization"]


def test_create_path_unknown_goal_returns_404(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "does-not-exist"}, headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "goal not found"


def test_create_path_skill_with_no_courses_returns_empty_list(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    body = response.json()
    data_viz_step = next(
        s for s in body["steps"] if s["skill"]["slug"] == "data-visualization"
    )
    assert data_viz_step["courses"] == []


def test_create_path_courses_are_difficulty_ordered(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    body = response.json()
    sql_step = next(s for s in body["steps"] if s["skill"]["slug"] == "sql")
    difficulty_rank = {"beginner": 0, "intermediate": 1, "advanced": 2, None: 3}
    assert len(sql_step["courses"]) > 0, "sql step should have ingested courses"
    ranks = [difficulty_rank[c["difficulty"]] for c in sql_step["courses"]]
    assert ranks == sorted(ranks)


def test_create_path_requires_auth():
    response = client.post("/paths", json={"goal_slug": "data-analyst"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run to verify the new/changed tests fail correctly**

Run: `venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: `test_create_path_requires_auth` FAILS (currently returns 200,
not 401); the other 4 tests currently FAIL too, since they now pass
`headers=auth_headers` to an endpoint that doesn't yet require or expect
it — but a request with valid unrelated headers should still succeed
today (endpoint doesn't reject extra headers), so verify by reading the
failure: if they fail, it should only be because `auth_headers` fixture
setup itself works fine and the assertions still hold pre-change (they
should PASS actually, since adding a header to an unauthenticated
endpoint doesn't break it) — the only test that should currently FAIL is
`test_create_path_requires_auth`. Confirm that's the only failure before
proceeding.

- [ ] **Step 3: Update `backend/routers/paths.py` to require auth and persist the goal**

Replace the full content of `backend/routers/paths.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user_id
from backend.db import get_connection
from backend.queries import (
    get_courses_for_skill,
    get_goal,
    get_goal_skills,
    upsert_user_goal,
)
from backend.schemas import CourseOut, GoalOut, PathStep, SkillOut

router = APIRouter()


class PathRequest(BaseModel):
    goal_slug: str


class PathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]


@router.post("/paths", response_model=PathResponse)
def create_path(
    request: PathRequest, user_id: str = Depends(get_current_user_id)
) -> PathResponse:
    conn = get_connection()
    try:
        goal = get_goal(conn, request.goal_slug)
        if goal is None:
            raise HTTPException(status_code=404, detail="goal not found")

        upsert_user_goal(conn, user_id, goal["id"])

        skills = get_goal_skills(conn, goal["id"])
        steps = [
            PathStep(
                skill=SkillOut(name=skill["name"], slug=skill["slug"]),
                courses=[
                    CourseOut(**course)
                    for course in get_courses_for_skill(conn, skill["id"])
                ],
            )
            for skill in skills
        ]
        return PathResponse(
            goal=GoalOut(name=goal["name"], slug=goal["slug"]),
            steps=steps,
        )
    finally:
        conn.close()
```

- [ ] **Step 4: Run to verify all `test_paths.py` tests now pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Fix `tests/test_cors.py`, which posted to `/paths` unauthenticated**

`/paths` now requires auth, so the CORS test (which only cares about the
CORS middleware, not this specific endpoint) needs to target a still-public
endpoint. Replace the full content of `tests/test_cors.py`:

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_cors_allows_frontend_dev_origin():
    response = client.get(
        "/courses",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 6: Verify the goal actually persisted**

Run:
```bash
venv/Scripts/python.exe -c "
import psycopg, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM user_goals')
print('user_goals rows:', cur.fetchone()[0])
"
```
Expected: at least 1 row (the test suite's `auth_headers` fixture creates
one test user and this task's tests call `POST /paths` against it
multiple times, upserting the same row each time — count should be a
small number, not zero).

- [ ] **Step 7: Run the full suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all 28 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/routers/paths.py tests/test_paths.py tests/test_cors.py
git commit -m "feat: require auth on POST /paths, persist chosen goal to user_goals"
```

---

## Task 6: `GET /me/path`, `POST /me/progress`, `DELETE /me/path`

**Files:**
- Create: `backend/routers/me.py`
- Modify: `backend/main.py`
- Create: `tests/test_me.py`

**Interfaces:**
- Consumes: `backend.auth.get_current_user_id` (Task 3);
  `backend.queries.get_user_goal`, `get_goal_skills`,
  `get_courses_for_skill`, `get_completed_course_ids`,
  `toggle_completed_course`, `delete_user_goal` (Task 4);
  `backend.schemas.PathStep`, `SkillOut`, `GoalOut`, `CourseOut`
  (Task 4).
- Produces: `GET /me/path` → `MePathResponse` (`goal: GoalOut`, `steps:
  list[PathStep]`, `completed_course_ids: list[str]`) or 404 `{"detail":
  "no goal set"}`; `POST /me/progress` (body `{"course_id": str}`) →
  `ProgressResponse` (`course_id: str`, `completed: bool`); `DELETE
  /me/path` → 204. All three require auth (401 without a valid token).
  Consumed by Task 7's frontend API client.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_me.py`:

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_my_path_returns_404_when_no_goal_set(auth_headers):
    response = client.get("/me/path", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "no goal set"


def test_full_progress_flow(auth_headers):
    create_response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    assert create_response.status_code == 200

    path_response = client.get("/me/path", headers=auth_headers)
    assert path_response.status_code == 200
    body = path_response.json()
    assert body["goal"] == {"name": "Data Analyst", "slug": "data-analyst"}
    assert body["completed_course_ids"] == []

    sql_step = next(s for s in body["steps"] if s["skill"]["slug"] == "sql")
    course_id = sql_step["courses"][0]["id"]

    toggle_response = client.post(
        "/me/progress", json={"course_id": course_id}, headers=auth_headers
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json() == {"course_id": course_id, "completed": True}

    path_response_2 = client.get("/me/path", headers=auth_headers)
    assert course_id in path_response_2.json()["completed_course_ids"]

    toggle_again_response = client.post(
        "/me/progress", json={"course_id": course_id}, headers=auth_headers
    )
    assert toggle_again_response.json() == {"course_id": course_id, "completed": False}

    path_response_3 = client.get("/me/path", headers=auth_headers)
    assert course_id not in path_response_3.json()["completed_course_ids"]

    clear_response = client.delete("/me/path", headers=auth_headers)
    assert clear_response.status_code == 204

    path_response_4 = client.get("/me/path", headers=auth_headers)
    assert path_response_4.status_code == 404


def test_me_path_requires_auth():
    response = client.get("/me/path")
    assert response.status_code == 401


def test_me_progress_requires_auth():
    response = client.post(
        "/me/progress", json={"course_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_me.py -v`
Expected: FAIL — 404 Not Found on every request (no `/me/*` routes exist
yet).

- [ ] **Step 3: Create `backend/routers/me.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth import get_current_user_id
from backend.db import get_connection
from backend.queries import (
    delete_user_goal,
    get_completed_course_ids,
    get_courses_for_skill,
    get_goal_skills,
    get_user_goal,
    toggle_completed_course,
)
from backend.schemas import CourseOut, GoalOut, PathStep, SkillOut

router = APIRouter(prefix="/me")


class MePathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]
    completed_course_ids: list[str]


class ProgressRequest(BaseModel):
    course_id: str


class ProgressResponse(BaseModel):
    course_id: str
    completed: bool


@router.get("/path", response_model=MePathResponse)
def get_my_path(user_id: str = Depends(get_current_user_id)) -> MePathResponse:
    conn = get_connection()
    try:
        goal = get_user_goal(conn, user_id)
        if goal is None:
            raise HTTPException(status_code=404, detail="no goal set")

        skills = get_goal_skills(conn, goal["id"])
        steps = [
            PathStep(
                skill=SkillOut(name=skill["name"], slug=skill["slug"]),
                courses=[
                    CourseOut(**course)
                    for course in get_courses_for_skill(conn, skill["id"])
                ],
            )
            for skill in skills
        ]
        completed_course_ids = get_completed_course_ids(conn, user_id)
        return MePathResponse(
            goal=GoalOut(name=goal["name"], slug=goal["slug"]),
            steps=steps,
            completed_course_ids=completed_course_ids,
        )
    finally:
        conn.close()


@router.post("/progress", response_model=ProgressResponse)
def toggle_progress(
    request: ProgressRequest, user_id: str = Depends(get_current_user_id)
) -> ProgressResponse:
    conn = get_connection()
    try:
        completed = toggle_completed_course(conn, user_id, request.course_id)
        return ProgressResponse(course_id=request.course_id, completed=completed)
    finally:
        conn.close()


@router.delete("/path", status_code=204)
def clear_my_path(user_id: str = Depends(get_current_user_id)) -> None:
    conn = get_connection()
    try:
        delete_user_goal(conn, user_id)
    finally:
        conn.close()
```

- [ ] **Step 4: Wire the new router into `backend/main.py`**

Replace the full content of `backend/main.py`:

```python
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.courses import router as courses_router
from backend.routers.me import router as me_router
from backend.routers.paths import router as paths_router

load_dotenv()

app = FastAPI(title="SkillPath API")

cors_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(paths_router)
app.include_router(courses_router)
app.include_router(me_router)
```

- [ ] **Step 5: Run to verify the tests pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_me.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 6: Run the full suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all 32 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/routers/me.py backend/main.py tests/test_me.py
git commit -m "feat: add GET/POST/DELETE /me/path and /me/progress endpoints"
```

---

## Task 7: Frontend Supabase client + auth-aware API calls

**Files:**
- Modify: `frontend/package.json` (via `npm install`)
- Create: `frontend/lib/supabaseClient.ts`
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Produces: `frontend/lib/supabaseClient.ts` exports `supabase` (a
  `SupabaseClient` instance) — consumed by Task 8's login/signup pages,
  Task 9's `useRequireAuth`, and this task's own `authHeaders` helper.
- Produces (added to `frontend/lib/api.ts`): `type ServerPath = { goal:
  GoalOut; steps: PathStep[]; completed_course_ids: string[] }`;
  `getMyPath(): Promise<ServerPath>` (throws `ApiError` with `status:
  404` when no goal set); `toggleProgress(courseId: string):
  Promise<{ course_id: string; completed: boolean }>`; `clearMyPath():
  Promise<void>`. `createPath` is modified to attach an `Authorization`
  header. Consumed by Task 10's `useServerPath` hook and Task 8's
  onboarding-adjacent auth flow.

- [ ] **Step 1: Install `@supabase/supabase-js`**

Run: `cd frontend && npm install @supabase/supabase-js`
(Let npm resolve and pin the current version in `package.json`/
`package-lock.json` — don't hand-edit a version string.)

- [ ] **Step 2: Create `frontend/lib/supabaseClient.ts`**

```ts
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY must be set in frontend/.env.local"
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

- [ ] **Step 3: Add an `authHeaders` helper and the three new functions/type to `frontend/lib/api.ts`**

Add this import at the top of `frontend/lib/api.ts`, alongside the
existing content (don't remove anything yet — that happens in the next
step):

```ts
import { supabase } from "@/lib/supabaseClient";
```

Add this helper function anywhere below the existing `handleResponse`
function:

```ts
async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
```

Add this type below the existing `CourseDetail` type:

```ts
export type ServerPath = {
  goal: GoalOut;
  steps: PathStep[];
  completed_course_ids: string[];
};
```

Append these three functions at the end of the file:

```ts
export async function getMyPath(): Promise<ServerPath> {
  const response = await fetch(`${API_BASE_URL}/me/path`, {
    headers: await authHeaders(),
  });
  return handleResponse<ServerPath>(response);
}

export async function toggleProgress(
  courseId: string
): Promise<{ course_id: string; completed: boolean }> {
  const response = await fetch(`${API_BASE_URL}/me/progress`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ course_id: courseId }),
  });
  return handleResponse<{ course_id: string; completed: boolean }>(response);
}

export async function clearMyPath(): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/me/path`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
}
```

- [ ] **Step 4: Attach auth headers to `createPath`**

In `frontend/lib/api.ts`, find the existing `createPath` function and
change its `fetch` call to merge in `authHeaders()`:

```ts
export async function createPath(goalSlug: string): Promise<PathResponse> {
  const response = await fetch(`${API_BASE_URL}/paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ goal_slug: goalSlug }),
  });
  return handleResponse<PathResponse>(response);
}
```

- [ ] **Step 5: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds (these new exports aren't consumed by any
screen yet — Tasks 10/11 wire them in — but everything must type-check
standalone).

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/lib/supabaseClient.ts frontend/lib/api.ts
git commit -m "feat: add Supabase client and auth-aware API calls"
```

---

## Task 8: Login and signup screens

**Files:**
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/signup/page.tsx`

**Interfaces:**
- Consumes: `supabase` from `frontend/lib/supabaseClient.ts` (Task 7).
- Produces: `/login` and `/signup` routes. Neither is consumed by
  another file's exports (leaf screens), but Task 9's `useRequireAuth`
  redirects to `/login` by name, so that route must exist with this
  exact path.

Per `DESIGN.md`'s login screen spec: email, password, forgot-password
line (no working flow — rendered as plain text, not a link, per the
spec's Non-goals), primary button, divider, sign-up link. No Google
button this sprint (Decision 3). Signup handles both possible Supabase
project configurations gracefully: if email confirmation is required
(no session returned), show an inline message rather than crash or
silently do nothing — the setup wizard should have disabled this
requirement for a frictionless flow, but the code doesn't assume that.

- [ ] **Step 1: Create `frontend/app/login/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setIsSubmitting(false);
    if (signInError) {
      setError("Incorrect email or password. Please try again.");
      return;
    }
    router.push("/onboarding");
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">Log in</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          required
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          required
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          Log in
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-sm text-muted">Forgot password?</p>

      <div className="border-t border-gray-200 pt-4 text-center text-sm">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="underline">
          Sign up
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/app/signup/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
    });
    setIsSubmitting(false);
    if (signUpError) {
      setError("Something went wrong creating your account. Please try again.");
      return;
    }
    if (!data.session) {
      setError("Check your email to confirm your account, then log in.");
      return;
    }
    router.push("/onboarding");
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">Sign up</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          required
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="password"
          required
          minLength={6}
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          Sign up
        </button>
      </form>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-sm text-muted">No credit card. No catch. Ever.</p>

      <div className="border-t border-gray-200 pt-4 text-center text-sm">
        Already have an account?{" "}
        <Link href="/login" className="underline">
          Log in
        </Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, open `http://localhost:3000/signup`, create
a test account with a real-looking email and a password of 6+
characters. If it redirects straight to `/onboarding`, email
confirmation is disabled on the local Supabase project (expected/
desired). If it shows the "check your email" message instead, open
`http://127.0.0.1:54324` (the local Supabase stack's Inbucket email
catcher — confirm the exact URL via `npx supabase status`), find the
confirmation email, and note in your task report that email
confirmation is ON — this is a real configuration decision the user
should be told about (Global Constraints assumed it would be off for a
frictionless signup).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/login/page.tsx frontend/app/signup/page.tsx
git commit -m "feat: add login and signup screens"
```

---

## Task 9: Route protection

**Files:**
- Create: `frontend/lib/useRequireAuth.ts`
- Modify: `frontend/app/(hub)/layout.tsx`
- Modify: `frontend/app/onboarding/page.tsx`

**Interfaces:**
- Consumes: `supabase` from `frontend/lib/supabaseClient.ts` (Task 7).
- Produces: `useRequireAuth(): boolean` — `true` once a valid session is
  confirmed present (redirects to `/login` and stays `false` otherwise).
  Consumed by `(hub)/layout.tsx` (covering `/`, `/browse`,
  `/course/[id]`, `/profile`) and `onboarding/page.tsx`.

- [ ] **Step 1: Create `frontend/lib/useRequireAuth.ts`**

```ts
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export function useRequireAuth(): boolean {
  const router = useRouter();
  const [isAuthChecked, setIsAuthChecked] = useState(false);

  useEffect(() => {
    let isMounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!isMounted) return;
      if (!data.session) {
        router.replace("/login");
      } else {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- session check is async and can't run during render
        setIsAuthChecked(true);
      }
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        router.replace("/login");
      }
    });

    return () => {
      isMounted = false;
      listener.subscription.unsubscribe();
    };
  }, [router]);

  return isAuthChecked;
}
```

- [ ] **Step 2: Apply it in `frontend/app/(hub)/layout.tsx`**

Replace the full content of `frontend/app/(hub)/layout.tsx`:

```tsx
"use client";

import { Nav } from "@/components/Nav";
import { useRequireAuth } from "@/lib/useRequireAuth";

export default function HubLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const isAuthChecked = useRequireAuth();

  if (!isAuthChecked) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col pb-16 md:pb-0">
      <Nav />
      <main className="flex-1">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Apply it in `frontend/app/onboarding/page.tsx`**

In `frontend/app/onboarding/page.tsx`, add the import and the check —
this is a partial edit, not a full replacement (Task 10 replaces more of
this file):

```tsx
import { useRequireAuth } from "@/lib/useRequireAuth";
```

Inside the `OnboardingPage` component, add near the top (after existing
`useState` calls):

```tsx
const isAuthChecked = useRequireAuth();
```

And right before the `return (` for the JSX, add:

```tsx
if (!isAuthChecked) {
  return null;
}
```

- [ ] **Step 4: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, in a private/incognito window (no existing
session) visit `http://localhost:3000/onboarding` directly — should
redirect to `/login`. Visit `http://localhost:3000/profile` directly —
should also redirect to `/login`. Log in, then both routes should render
normally.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/useRequireAuth.ts "frontend/app/(hub)/layout.tsx" frontend/app/onboarding/page.tsx
git commit -m "feat: require login before onboarding and all hub routes"
```

---

## Task 10: `useServerPath` hook; simplify onboarding

**Files:**
- Create: `frontend/lib/useServerPath.ts`
- Delete: `frontend/lib/useLocalPath.ts`
- Modify: `frontend/app/onboarding/page.tsx`

**Interfaces:**
- Consumes: `getMyPath`, `toggleProgress`, `clearMyPath`, `ApiError`,
  `type ServerPath` from `frontend/lib/api.ts` (Task 7).
- Produces: `useServerPath(): { path: ServerPath | null; isLoaded:
  boolean; refresh: () => Promise<void>; toggleCourseComplete:
  (courseId: string) => Promise<void>; isCourseComplete: (courseId:
  string) => boolean; clearPath: () => Promise<void> }` — this REPLACES
  `useLocalPath`'s `{ path, isLoaded, savePath, toggleCourseComplete,
  isCourseComplete, clearPath }` shape. Note `savePath` is gone (the
  backend persists automatically on `POST /paths` now — see Task 5) and
  `toggleCourseComplete`/`clearPath` are now `Promise`-returning instead
  of synchronous. Consumed by Task 11's screens.

- [ ] **Step 1: Create `frontend/lib/useServerPath.ts`**

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, clearMyPath, getMyPath, toggleProgress, type ServerPath } from "@/lib/api";

export type { ServerPath };

export function useServerPath() {
  const [path, setPath] = useState<ServerPath | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await getMyPath();
      setPath(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setPath(null);
      } else {
        throw err;
      }
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetching the current user's path requires an async call, can't run during render
    refresh().finally(() => setIsLoaded(true));
  }, [refresh]);

  const toggleCourseComplete = useCallback(async (courseId: string) => {
    const result = await toggleProgress(courseId);
    setPath((current) => {
      if (!current) return current;
      const completed_course_ids = result.completed
        ? [...current.completed_course_ids, courseId]
        : current.completed_course_ids.filter((id) => id !== courseId);
      return { ...current, completed_course_ids };
    });
  }, []);

  const isCourseComplete = useCallback(
    (courseId: string) => path?.completed_course_ids.includes(courseId) ?? false,
    [path]
  );

  const clearPath = useCallback(async () => {
    await clearMyPath();
    setPath(null);
  }, []);

  return { path, isLoaded, refresh, toggleCourseComplete, isCourseComplete, clearPath };
}
```

- [ ] **Step 2: Delete `frontend/lib/useLocalPath.ts`**

```bash
git rm frontend/lib/useLocalPath.ts
```

- [ ] **Step 3: Simplify `frontend/app/onboarding/page.tsx`**

`createPath` now persists the goal server-side (Task 5), so onboarding
no longer needs to call any path-saving function itself — it only needs
to submit the goal and navigate; the hub page's own `useServerPath`
fetches the freshly-persisted path when it mounts. Replace the full
content of `frontend/app/onboarding/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, createPath } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";

const POPULAR_GOALS = [{ label: "Data analyst", slug: "data-analyst" }];

export default function OnboardingPage() {
  const router = useRouter();
  const isAuthChecked = useRequireAuth();
  const [goalSlug, setGoalSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitGoal(slug: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      await createPath(slug);
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("We don't have a path for that goal yet.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isAuthChecked) {
    return null;
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">What do you want to learn?</h1>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (goalSlug.trim()) submitGoal(goalSlug.trim());
        }}
        className="flex flex-col gap-3"
      >
        <input
          type="text"
          value={goalSlug}
          onChange={(e) => setGoalSlug(e.target.value)}
          placeholder="e.g. data-analyst"
          className="rounded border border-gray-300 px-4 py-3 text-base"
        />
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-3 font-medium text-white disabled:opacity-50"
        >
          Build my path
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {POPULAR_GOALS.map((goal) => (
          <button
            key={goal.slug}
            onClick={() => submitGoal(goal.slug)}
            disabled={isSubmitting}
            className="rounded-full border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
          >
            {goal.label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <p className="text-sm text-muted">No credit card. No catch. Ever.</p>
    </div>
  );
}
```

- [ ] **Step 4: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds. (Task 11 still needs to update the four
screens that import the now-deleted `useLocalPath` — this step's build
will FAIL until Task 11 is done if those imports are checked eagerly;
if `npm run build` fails here solely because of unresolved
`useLocalPath` imports in files this task didn't touch, that's expected
and gets fixed in Task 11, not a sign this task did something wrong.
Confirm the failure (if any) is specifically about those other files'
imports, not about `onboarding/page.tsx` or `useServerPath.ts`
themselves.)

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/useServerPath.ts frontend/app/onboarding/page.tsx
git commit -m "feat: add useServerPath hook, simplify onboarding"
```

---

## Task 11: Migrate remaining screens to `useServerPath`

**Files:**
- Modify: `frontend/app/(hub)/page.tsx`
- Modify: `frontend/components/Dashboard.tsx`
- Modify: `frontend/app/(hub)/profile/page.tsx`
- Modify: `frontend/app/(hub)/course/[id]/page.tsx`

**Interfaces:**
- Consumes: `useServerPath`, `type ServerPath` from
  `frontend/lib/useServerPath.ts` (Task 10).
- Produces: nothing new consumed by later tasks — this is the last
  screen-level task before deploy prep.

- [ ] **Step 1: Update `frontend/app/(hub)/page.tsx`**

Replace the full content:

```tsx
"use client";

import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useServerPath } from "@/lib/useServerPath";

export default function HomePage() {
  const { path, isLoaded, isCourseComplete } = useServerPath();

  if (!isLoaded) {
    return null;
  }

  if (!path) {
    return <Landing />;
  }

  return <Dashboard path={path} isCourseComplete={isCourseComplete} />;
}
```

- [ ] **Step 2: Update `frontend/components/Dashboard.tsx`'s import**

In `frontend/components/Dashboard.tsx`, change only the import line —
everything else in the file (all the JSX and logic) is unchanged, since
`Dashboard` never reads `completedCourseIds`/`completed_course_ids`
directly, only via the `isCourseComplete` prop function:

```tsx
import type { ServerPath } from "@/lib/useServerPath";
```

And change the prop type annotation from `path: StoredPath` to
`path: ServerPath`:

```tsx
export function Dashboard({
  path,
  isCourseComplete,
}: {
  path: ServerPath;
  isCourseComplete: (courseId: string) => boolean;
}) {
```

- [ ] **Step 3: Update `frontend/app/(hub)/profile/page.tsx`**

Replace the full content:

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useServerPath } from "@/lib/useServerPath";

export default function ProfilePage() {
  const router = useRouter();
  const { path, isLoaded, isCourseComplete, clearPath } = useServerPath();

  const allCourses = path?.steps.flatMap((step) => step.courses) ?? [];
  const completedCount = allCourses.filter((c) => isCourseComplete(c.id)).length;
  const totalMinutes = allCourses
    .filter((c) => isCourseComplete(c.id))
    .reduce((sum, c) => sum + (c.duration_minutes ?? 0), 0);
  const hoursLearned = Math.round(totalMinutes / 60);

  async function handleChangeGoal() {
    await clearPath();
    router.push("/onboarding");
  }

  if (!isLoaded) {
    return null;
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <h1 className="text-xl font-bold">Your progress</h1>

      <div className="flex gap-4 text-sm">
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {completedCount} courses done
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {hoursLearned} hours learned
        </span>
      </div>

      <div>
        <h2 className="mb-2 font-medium">Your paths</h2>
        {!path && (
          <p className="text-sm text-muted">
            No path started yet.{" "}
            <Link href="/onboarding" className="underline">
              Set a goal
            </Link>
            .
          </p>
        )}
        {path && (
          <>
            <Link
              href="/"
              className="flex items-center justify-between border-y border-gray-200 py-3"
            >
              <span>{path.goal.name}</span>
              <span className="text-sm text-muted">
                {completedCount}/{allCourses.length} complete
              </span>
            </Link>
            <button
              onClick={handleChangeGoal}
              className="mt-3 text-sm underline text-muted"
            >
              Change goal
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

(Only change from the Sprint 3 version: the import switches from
`useLocalPath` to `useServerPath`, and `handleChangeGoal` becomes
`async`/`await`s `clearPath()` since it's now a network call. Everything
else is byte-for-byte identical — this task does not redesign this
screen.)

- [ ] **Step 4: Update `frontend/app/(hub)/course/[id]/page.tsx`**

In `frontend/app/(hub)/course/[id]/page.tsx`, change only the import
line:

```tsx
import { useServerPath } from "@/lib/useServerPath";
```

And the hook call:

```tsx
const { path, isLoaded, toggleCourseComplete, isCourseComplete } = useServerPath();
```

Everything else in the file — the fetch effect, the step/stepIndex
derivation, the JSX, the button's `onClick={() =>
toggleCourseComplete(course.id)}` — stays exactly as it is. The button's
`onClick` calling an async function without awaiting it is fine here
(matches the existing fire-and-forget pattern); this task doesn't add
new error-handling UX for a failed toggle, since that's outside this
task's scope (swapping the data source, not redesigning error states).

- [ ] **Step 5: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds, no remaining references to `useLocalPath` or
`StoredPath` anywhere (search the `frontend/` tree to confirm — `grep -r
useLocalPath frontend/` should return nothing).

- [ ] **Step 6: Manual end-to-end check**

With the backend running (`npm run dev:backend` from the repo root) and
`npm run dev:frontend`, and `npx supabase start` already running:
sign up or log in → onboarding → pick "Data analyst" → dashboard shows
the path → click a course → mark complete → back to dashboard, progress
bar reflects it → profile page shows the updated stats → refresh the
page entirely (hard reload) → progress should still be there (proving
it's server-persisted, not just in-memory).

- [ ] **Step 7: Commit**

```bash
git add "frontend/app/(hub)/page.tsx" frontend/components/Dashboard.tsx "frontend/app/(hub)/profile/page.tsx" "frontend/app/(hub)/course/[id]/page.tsx"
git commit -m "feat: migrate dashboard, profile, and course detail to useServerPath"
```

---

## Task 12: Sign-out control

**Files:**
- Modify: `frontend/app/(hub)/profile/page.tsx`

**Interfaces:**
- Consumes: `supabase` from `frontend/lib/supabaseClient.ts` (Task 7).
- Produces: nothing consumed by later tasks — leaf UI addition.

- [ ] **Step 1: Add a sign-out handler and button to the profile page**

In `frontend/app/(hub)/profile/page.tsx`, add the import:

```tsx
import { supabase } from "@/lib/supabaseClient";
```

Add a handler function alongside the existing `handleChangeGoal`:

```tsx
async function handleSignOut() {
  await supabase.auth.signOut();
  router.push("/login");
}
```

Add a sign-out button at the end of the page's returned JSX, just before
the closing `</div>` of the outermost container:

```tsx
      <button
        onClick={handleSignOut}
        className="text-sm underline text-muted"
      >
        Log out
      </button>
    </div>
  );
}
```

(This replaces the previous closing `</div>\n  );\n}` — the button goes
inside the outer container, after the "Your paths" section.)

- [ ] **Step 2: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, log in, go to `/profile`, click "Log out" —
should redirect to `/login`; then visiting `/profile` directly again
should redirect to `/login` too (confirming the session actually
cleared, not just the button navigating away).

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/(hub)/profile/page.tsx"
git commit -m "feat: add sign-out control to profile page"
```

---

## Task 13: Point the prod smoke-test stack at the Supabase CLI stack

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `start-sp-prod.bat`

**Interfaces:**
- Produces: nothing consumed by other tasks — this is the last task,
  closing out the "local dev/prod tooling still assumes a plain
  Postgres container" gap left by Decision 4.

The prod smoke-test stack's own `db` service (a plain `postgres:16`
container) can't run Supabase Auth. Rather than stand up a third
database, its backend container points at the same Supabase CLI local
stack the dev backend already uses — reached via `host.docker.internal`
since the Supabase CLI's stack runs as separate Docker containers, not
inside `docker-compose.prod.yml`'s own network. The Supabase CLI's
default local Postgres port is `54322` — if `npx supabase status` shows
a different port for this project (customized in `supabase/config.toml`),
adjust the port below to match.

- [ ] **Step 1: Remove the `db` service and its volume from `docker-compose.prod.yml`**

Read the current file, then remove the entire `db:` service block (the
`image: postgres:16` through its `healthcheck:` section) and the
`skillpath_pgdata_prod:` line under `volumes:` at the bottom. Remove the
`depends_on: db: condition: service_healthy` block from the `backend`
service too, since there's no longer a `db` service in this file to
depend on.

- [ ] **Step 2: Point the backend's `DATABASE_URL` at the Supabase CLI stack via `host.docker.internal`**

In the `backend` service's `environment:` block, change `DATABASE_URL`
to:

```yaml
      DATABASE_URL: postgresql://postgres:postgres@host.docker.internal:54322/postgres
```

(The Supabase CLI's local stack uses a fixed default database name/user
of `postgres`/`postgres` on port `54322` — verify this matches your
actual `npx supabase status` output and adjust if your project's
`supabase/config.toml` customized it.)

- [ ] **Step 3: Add a startup check to `start-sp-prod.bat`**

The prod smoke test now depends on the Supabase CLI stack already
running. Replace the full content of `start-sp-prod.bat`:

```bat
@echo off
cd /d "%~dp0"
npx supabase status >nul 2>&1
if errorlevel 1 (
    echo Supabase local stack is not running. Start it first with: npx supabase start
    pause
    exit /b 1
)
docker compose -f docker-compose.prod.yml down -v
if errorlevel 1 (
    pause
    exit /b %errorlevel%
)
docker compose -f docker-compose.prod.yml up -d --build
if errorlevel 1 pause
exit /b %errorlevel%
```

- [ ] **Step 4: Verify the compose file is still syntactically valid**

Run: `docker compose -f docker-compose.prod.yml config`
Expected: valid YAML output, no `db` service present, `backend`'s
`DATABASE_URL` shows the `host.docker.internal:54322` value.

- [ ] **Step 5: Live smoke test (if Docker Desktop is available and `npx supabase start` is running)**

Run: `start-sp-prod.bat` (or the equivalent `docker compose -f
docker-compose.prod.yml down -v && up -d --build` directly)
Expected: backend and frontend containers start; `curl -s -X POST
http://localhost:8001/paths -H "Content-Type: application/json" -H
"Authorization: Bearer <a real token>" -d '{"goal_slug":"data-analyst"}'`
returns a valid response (you'll need a real JWT — either sign in via
the deployed-mode frontend at `http://localhost:3001` and copy the token
from browser dev tools, or reuse `tests/auth_helpers.make_test_jwt` with
a test user id). Clean up afterward with `stop-sp-prod.bat`.

If Docker Desktop isn't available in your environment, skip this step
and note it in your report — the `docker compose config` validation in
Step 4 is the fallback verification.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.prod.yml start-sp-prod.bat
git commit -m "fix: point prod smoke-test backend at Supabase CLI local stack"
```

---

## Post-plan note: deployment

This plan ends with the app working end-to-end against the local
Supabase CLI stack. Actual deployment (Render for the backend, Vercel
for the frontend, pushing migrations to the hosted Supabase project via
`supabase db push`, and copying hosted project keys into each platform's
environment variables) is Decision 8 in the design spec — a separate,
later piece of work once this plan's code is reviewed and merged. It
should get its own short wizard script (Render account, Vercel account,
hosted Supabase keys) rather than being folded into this plan, per the
scoping decision made when `scripts/setup-sprint4-dev.sh` was built.
