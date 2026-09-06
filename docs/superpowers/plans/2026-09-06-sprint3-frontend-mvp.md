# Sprint 3 Frontend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Next.js frontend (landing, onboarding, dashboard,
search/browse, course detail, profile) wired to the real FastAPI backend,
plus the two new backend endpoints those screens need.

**Architecture:** New `frontend/` Next.js (App Router, TypeScript, Tailwind)
project at the repo root, calling FastAPI directly from the browser (CORS
enabled). Selected goal/path and step-completion progress live in
`localStorage` only — no new database tables this sprint. Backend gains
`GET /courses` (search/browse) and `GET /courses/{id}` (detail), since the
existing `POST /paths` only serves the onboarding→dashboard flow.

**Tech Stack:** Next.js (App Router) + TypeScript + Tailwind CSS on the
frontend; FastAPI + psycopg (raw SQL, no ORM) on the backend — same stack
Sprint 2 already uses. No new Python dependencies (CORS is built into
FastAPI/Starlette). No frontend test framework this sprint (see Global
Constraints).

**Spec:** `docs/superpowers/specs/2026-09-06-sprint3-frontend-mvp-design.md`

## Global Constraints

- Progress/current-path state is `localStorage`-only this sprint — no
  `users`/`user_goals`/progress tables (Decision 1 in the spec).
- Frontend calls FastAPI directly from the browser at
  `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`) — no Next.js
  API-route proxy (Decision 2).
- No frontend automated tests this sprint (brainstorming decision) —
  frontend tasks verify via `npm run build` (TypeScript/build errors) and a
  manual dev-server check instead of a red/green test cycle. Backend tasks
  keep the existing pytest + real-Postgres pattern from Sprint 2.
- All UI copy, layout, spacing, and color-role decisions come from
  `docs/superpowers/specs/DESIGN.md` — don't invent new copy or layout not
  specified there or in this plan.
- Local Docker Postgres (`skillpath_db`) must be running for every backend
  test task: `docker ps` should show it healthy before running `pytest`.

---

## Task 1: Extract shared response schemas

`routers/paths.py` currently defines `SkillOut`, `GoalOut`, and `CourseOut`
inline. The new courses router needs the same `SkillOut`/`CourseOut` shapes,
so pull the shared ones into a common module first — a small refactor, not
new behavior. Existing tests must pass unchanged (same JSON shape).

**Files:**
- Create: `backend/schemas.py`
- Modify: `backend/routers/paths.py`
- Test: `tests/test_paths.py` (no changes — must still pass as-is)

**Interfaces:**
- Produces: `backend.schemas.SkillOut` (`name: str`, `slug: str`),
  `backend.schemas.GoalOut` (`name: str`, `slug: str`),
  `backend.schemas.CourseOut` (`id: str`, `title: str`, `url: str`,
  `difficulty: str | None`, `duration_minutes: int | None`) — used by
  Task 3 and Task 4.

- [ ] **Step 1: Create `backend/schemas.py` with the shared models**

```python
from pydantic import BaseModel


class SkillOut(BaseModel):
    name: str
    slug: str


class GoalOut(BaseModel):
    name: str
    slug: str


class CourseOut(BaseModel):
    id: str
    title: str
    url: str
    difficulty: str | None
    duration_minutes: int | None
```

- [ ] **Step 2: Update `backend/routers/paths.py` to import instead of redefine**

Replace the top of `backend/routers/paths.py` (the `CourseOut`, `SkillOut`,
`GoalOut` class definitions) with an import, keeping `PathRequest`,
`PathStep`, `PathResponse` as they are:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import get_courses_for_skill, get_goal, get_goal_skills
from backend.schemas import CourseOut, GoalOut, SkillOut

router = APIRouter()


class PathRequest(BaseModel):
    goal_slug: str


class PathStep(BaseModel):
    skill: SkillOut
    courses: list[CourseOut]


class PathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]
```

(The `@router.post("/paths", ...)` function below this is unchanged.)

- [ ] **Step 3: Run the existing test suite to confirm nothing broke**

Run: `venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: all 4 tests still PASS, identical JSON shape as before.

- [ ] **Step 4: Commit**

```bash
git add backend/schemas.py backend/routers/paths.py
git commit -m "refactor: extract shared response schemas into backend/schemas.py"
```

---

## Task 2: Enable CORS for the Next.js dev origin

**Files:**
- Modify: `backend/main.py`
- Test: `tests/test_cors.py` (new)

**Interfaces:**
- Consumes: `backend.main.app` (existing `FastAPI` instance).
- Produces: nothing new consumed by later tasks — this is a middleware
  change, verified independently.

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_cors_allows_frontend_dev_origin():
    response = client.post(
        "/paths",
        json={"goal_slug": "data-analyst"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_cors.py -v`
Expected: FAIL — `KeyError: 'access-control-allow-origin'`

- [ ] **Step 3: Add CORS middleware**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.paths import router

app = FastAPI(title="SkillPath API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_cors.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all tests PASS (9 total after this task).

- [ ] **Step 6: Commit**

```bash
git add backend/main.py tests/test_cors.py
git commit -m "feat: enable CORS for the Next.js dev origin"
```

---

## Task 3: Backend — `GET /courses` (search/browse)

Resolves the deferred "no `LIMIT` on courses-per-skill" item for this new
endpoint: pagination is required, not optional, from the start.

**Files:**
- Modify: `backend/queries.py`
- Create: `backend/routers/courses.py`
- Modify: `backend/main.py`
- Test: `tests/test_courses.py` (new)

**Interfaces:**
- Consumes: `backend.schemas.SkillOut`, `backend.schemas.CourseOut`
  (Task 1); `backend.db.get_connection()`.
- Produces: `backend.queries.list_courses(conn, search, skill_slug, limit,
  offset) -> tuple[list[dict], int]` — each dict has keys `id`, `title`,
  `url`, `difficulty`, `duration_minutes`, `skills` (`list[dict]` with
  `name`/`slug`); second tuple element is the total matching count (for
  pagination). Used by Task 4's router only indirectly (separate query
  function); the `GET /courses` route itself at `/courses`.

- [ ] **Step 1: Write the failing test**

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_courses_returns_paginated_results():
    response = client.get("/courses", params={"limit": 5, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert "courses" in body and "total" in body
    assert len(body["courses"]) <= 5
    assert body["total"] >= len(body["courses"])


def test_list_courses_filters_by_skill():
    response = client.get("/courses", params={"skill": "sql", "limit": 50})
    body = response.json()
    assert len(body["courses"]) > 0
    for course in body["courses"]:
        assert any(s["slug"] == "sql" for s in course["skills"])


def test_list_courses_search_by_title():
    response = client.get("/courses", params={"search": "sql", "limit": 50})
    body = response.json()
    assert len(body["courses"]) > 0
    for course in body["courses"]:
        assert "sql" in course["title"].lower()


def test_list_courses_default_limit_is_20():
    response = client.get("/courses")
    body = response.json()
    assert len(body["courses"]) <= 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_courses.py -v`
Expected: FAIL — 404 (no `/courses` route yet).

- [ ] **Step 3: Add `list_courses` to `backend/queries.py`**

Append to `backend/queries.py`:

```python
def list_courses(
    conn: psycopg.Connection,
    search: str | None,
    skill_slug: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict], int]:
    where_clauses = []
    params: list = []

    if search:
        where_clauses.append("c.title ILIKE %s")
        params.append(f"%{search}%")

    if skill_slug:
        where_clauses.append(
            "c.id IN (SELECT cs.course_id FROM course_skills cs "
            "JOIN skills sk ON sk.id = cs.skill_id WHERE sk.slug = %s)"
        )
        params.append(skill_slug)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM courses c {where_sql}", params)
        total = cur.fetchone()[0]

        cur.execute(
            f"""
            SELECT c.id, c.title, c.url, c.difficulty, c.duration_minutes
            FROM courses c
            {where_sql}
            ORDER BY c.ingested_at DESC
            LIMIT %s OFFSET %s
            """,
            [*params, limit, offset],
        )
        courses = [
            {
                "id": str(r[0]),
                "title": r[1],
                "url": r[2],
                "difficulty": r[3],
                "duration_minutes": r[4],
            }
            for r in cur.fetchall()
        ]

        for course in courses:
            cur.execute(
                """
                SELECT sk.name, sk.slug
                FROM course_skills cs
                JOIN skills sk ON sk.id = cs.skill_id
                WHERE cs.course_id = %s
                """,
                (course["id"],),
            )
            course["skills"] = [{"name": r[0], "slug": r[1]} for r in cur.fetchall()]

        return courses, total
```

- [ ] **Step 4: Create `backend/routers/courses.py`**

```python
from fastapi import APIRouter
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import list_courses
from backend.schemas import CourseOut, SkillOut

router = APIRouter()


class CourseListItem(CourseOut):
    skills: list[SkillOut]


class CourseListResponse(BaseModel):
    courses: list[CourseListItem]
    total: int


@router.get("/courses", response_model=CourseListResponse)
def list_courses_endpoint(
    search: str | None = None,
    skill: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> CourseListResponse:
    conn = get_connection()
    try:
        courses, total = list_courses(conn, search, skill, limit, offset)
        return CourseListResponse(
            courses=[CourseListItem(**course) for course in courses],
            total=total,
        )
    finally:
        conn.close()
```

- [ ] **Step 5: Wire the new router into `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.courses import router as courses_router
from backend.routers.paths import router as paths_router

app = FastAPI(title="SkillPath API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(paths_router)
app.include_router(courses_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_courses.py -v`
Expected: all 4 PASS.

- [ ] **Step 7: Run the full backend suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all tests PASS (13 total after this task).

- [ ] **Step 8: Commit**

```bash
git add backend/queries.py backend/routers/courses.py backend/main.py tests/test_courses.py
git commit -m "feat: add GET /courses search/browse endpoint"
```

---

## Task 4: Backend — `GET /courses/{id}` (detail)

**Files:**
- Modify: `backend/queries.py`
- Modify: `backend/routers/courses.py`
- Test: `tests/test_courses.py`

**Interfaces:**
- Consumes: `backend.schemas.CourseOut`, `backend.schemas.SkillOut`
  (Task 1); `backend.routers.courses.router` (Task 3).
- Produces: `backend.queries.get_course_by_id(conn, course_id) -> dict |
  None` — dict has `id`, `title`, `url`, `description`, `difficulty`,
  `duration_minutes`, `source_name`, `skills` (`list[dict]`). Route
  `GET /courses/{course_id}` returns 404 with `detail: "course not found"`
  when missing (same pattern as `POST /paths`'s unknown-goal 404).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_courses.py`:

```python
def test_get_course_returns_detail():
    list_response = client.get("/courses", params={"skill": "sql", "limit": 1})
    course_id = list_response.json()["courses"][0]["id"]

    response = client.get(f"/courses/{course_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == course_id
    assert "description" in body
    assert "source_name" in body
    assert len(body["skills"]) > 0


def test_get_course_unknown_id_returns_404():
    response = client.get("/courses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "course not found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv/Scripts/python.exe -m pytest tests/test_courses.py -v`
Expected: FAIL — 404 (no `/courses/{id}` route yet) on the first new test.

- [ ] **Step 3: Add `get_course_by_id` to `backend/queries.py`**

Append to `backend/queries.py`:

```python
def get_course_by_id(conn: psycopg.Connection, course_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.title, c.url, c.description, c.difficulty,
                   c.duration_minutes, s.name
            FROM courses c
            JOIN sources s ON s.id = c.source_id
            WHERE c.id = %s
            """,
            (course_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            """
            SELECT sk.name, sk.slug
            FROM course_skills cs
            JOIN skills sk ON sk.id = cs.skill_id
            WHERE cs.course_id = %s
            """,
            (course_id,),
        )
        skills = [{"name": r[0], "slug": r[1]} for r in cur.fetchall()]

        return {
            "id": str(row[0]),
            "title": row[1],
            "url": row[2],
            "description": row[3],
            "difficulty": row[4],
            "duration_minutes": row[5],
            "source_name": row[6],
            "skills": skills,
        }
```

- [ ] **Step 4: Add the route to `backend/routers/courses.py`**

Add to `backend/routers/courses.py` (below the existing imports, extend
them with `HTTPException` and `get_course_by_id`):

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import get_course_by_id, list_courses
from backend.schemas import CourseOut, SkillOut

router = APIRouter()


class CourseListItem(CourseOut):
    skills: list[SkillOut]


class CourseListResponse(BaseModel):
    courses: list[CourseListItem]
    total: int


class CourseDetailResponse(CourseOut):
    description: str | None
    source_name: str
    skills: list[SkillOut]


@router.get("/courses", response_model=CourseListResponse)
def list_courses_endpoint(
    search: str | None = None,
    skill: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> CourseListResponse:
    conn = get_connection()
    try:
        courses, total = list_courses(conn, search, skill, limit, offset)
        return CourseListResponse(
            courses=[CourseListItem(**course) for course in courses],
            total=total,
        )
    finally:
        conn.close()


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
def get_course_endpoint(course_id: str) -> CourseDetailResponse:
    conn = get_connection()
    try:
        course = get_course_by_id(conn, course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="course not found")
        return CourseDetailResponse(**course)
    finally:
        conn.close()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv/Scripts/python.exe -m pytest tests/test_courses.py -v`
Expected: all 6 PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all tests PASS (15 total after this task). This completes all
backend work for Sprint 3.

- [ ] **Step 7: Commit**

```bash
git add backend/queries.py backend/routers/courses.py tests/test_courses.py
git commit -m "feat: add GET /courses/{id} detail endpoint"
```

---

## Task 5: Scaffold the Next.js frontend + Tailwind theme

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Modify: `frontend/tailwind.config.ts`
- Modify: `frontend/app/globals.css`
- Create: `frontend/.env.local` (gitignored by the scaffold's default `.gitignore`)
- Create: `frontend/.env.local.example`

**Interfaces:**
- Produces: Tailwind color tokens `accent`, `success`, `warning`, `muted`
  (used by every later frontend task instead of hardcoded hex values, per
  `DESIGN.md` section 8) and the env var `NEXT_PUBLIC_API_BASE_URL`
  (consumed by Task 7's `lib/api.ts`).

- [ ] **Step 1: Scaffold the project**

Run from the repo root:

```bash
npx create-next-app@latest frontend --typescript --eslint --tailwind --app --no-src-dir --import-alias "@/*" --use-npm
```

If prompted interactively (flags should suppress this, but versions vary):
TypeScript = Yes, ESLint = Yes, Tailwind CSS = Yes, `src/` directory = No,
App Router = Yes, import alias = `@/*`, Turbopack = No (accept default if
asked).

- [ ] **Step 2: Add semantic color tokens**

`create-next-app` scaffolds either Tailwind v3 (a `frontend/tailwind.config.ts`
file exists) or Tailwind v4 (no config file — theming lives in
`frontend/app/globals.css` via an `@theme` block, and the file starts with
`@import "tailwindcss";`). Check which one was generated and follow the
matching branch:

**If `frontend/tailwind.config.ts` exists (v3):** add a `colors` block
under `theme.extend`, keeping whatever `content` paths were generated:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: "#2563eb",
        success: "#16a34a",
        warning: "#d97706",
        muted: "#6b7280",
      },
    },
  },
  plugins: [],
};

export default config;
```

**If there's no `tailwind.config.ts` (v4):** add an `@theme` block to the
top of `frontend/app/globals.css`, right after the `@import "tailwindcss";`
line:

```css
@import "tailwindcss";

@theme {
  --color-accent: #2563eb;
  --color-success: #16a34a;
  --color-warning: #d97706;
  --color-muted: #6b7280;
}
```

Either branch makes `accent`/`success`/`warning`/`muted` available as
Tailwind color utilities (`bg-accent`, `text-success`, etc.) used in every
later frontend task — the utility class names in later tasks are identical
regardless of which branch was taken.

- [ ] **Step 3: Set the API base URL env var**

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Create `frontend/.env.local.example` (this one IS committed, as a template):

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 4: Verify the scaffold builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no TypeScript errors (default starter page).

- [ ] **Step 5: Commit**

```bash
git add frontend/ -- ':!frontend/node_modules' ':!frontend/.next' ':!frontend/.env.local'
git commit -m "feat: scaffold Next.js frontend with Tailwind theme tokens"
```

---

## Task 6: Shared layout + persistent nav

Per `DESIGN.md` section 4: `/onboarding` is the one route outside the
shared layout; dashboard (`/`), browse, course detail, and profile share
one persistent-nav layout as hub-and-spoke siblings.

**Files:**
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/components/Nav.tsx`

**Interfaces:**
- Produces: `<Nav />` component (no props) rendered inside the root layout;
  links to `/` (dashboard), `/browse`, `/profile`. `/onboarding` is NOT
  linked from `Nav` since it's the pre-hub entry point, not a hub
  destination.

- [ ] **Step 1: Create `frontend/components/Nav.tsx`**

```tsx
import Link from "next/link";

export function Nav() {
  return (
    <nav className="flex items-center justify-around border-t border-gray-200 bg-white px-4 py-3 md:justify-start md:gap-8 md:border-b md:border-t-0">
      <Link href="/" className="text-sm font-medium text-gray-900">
        Dashboard
      </Link>
      <Link href="/browse" className="text-sm font-medium text-gray-900">
        Browse
      </Link>
      <Link href="/profile" className="text-sm font-medium text-gray-900">
        Profile
      </Link>
    </nav>
  );
}
```

(Mobile-first per `DESIGN.md` section 7: base classes put nav items in a
bottom bar `justify-around`; `md:` layers on a top bar with left-aligned
links.)

- [ ] **Step 2: Wire `Nav` into the root layout**

Replace the body of `frontend/app/layout.tsx` (generated by
`create-next-app`) with:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "SkillPath",
  description: "Free, step-by-step learning paths toward any skill.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-gray-900">
        <div className="flex min-h-screen flex-col pb-16 md:pb-0">
          <Nav />
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
```

(Nav renders as a bottom bar on mobile — hence `pb-16` on the wrapper so
content doesn't sit underneath it; on `md:` it becomes a top bar instead.)

- [ ] **Step 3: Verify it builds and renders**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, open `http://localhost:3000` — nav bar with
Dashboard/Browse/Profile links visible.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/layout.tsx frontend/components/Nav.tsx
git commit -m "feat: add shared layout with persistent nav"
```

---

## Task 7: API client + local path/progress hook

This is the integration seam every screen task after this one depends on.

**Files:**
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/useLocalPath.ts`

**Interfaces:**
- Produces (from `lib/api.ts`):
  - `type SkillOut = { name: string; slug: string }`
  - `type GoalOut = { name: string; slug: string }`
  - `type CourseOut = { id: string; title: string; url: string; difficulty: string | null; duration_minutes: number | null }`
  - `type PathStep = { skill: SkillOut; courses: CourseOut[] }`
  - `type PathResponse = { goal: GoalOut; steps: PathStep[] }`
  - `type CourseListItem = CourseOut & { skills: SkillOut[] }`
  - `type CourseDetail = CourseOut & { description: string | null; source_name: string; skills: SkillOut[] }`
  - `class ApiError extends Error { status: number }`
  - `createPath(goalSlug: string): Promise<PathResponse>` — throws
    `ApiError` with `status: 404` when the goal slug is unknown.
  - `listCourses(params: { search?: string; skill?: string; limit?: number; offset?: number }): Promise<{ courses: CourseListItem[]; total: number }>`
  - `getCourse(id: string): Promise<CourseDetail>` — throws `ApiError` with
    `status: 404` when the course doesn't exist.
- Produces (from `lib/useLocalPath.ts`):
  - `type StoredPath = { goal: GoalOut; steps: PathStep[]; completedCourseIds: string[] }`
  - `useLocalPath(): { path: StoredPath | null; savePath: (path: PathResponse) => void; toggleCourseComplete: (courseId: string) => void; isCourseComplete: (courseId: string) => boolean; clearPath: () => void }`
- Consumes: Task 5's `NEXT_PUBLIC_API_BASE_URL` env var.

- [ ] **Step 1: Create `frontend/lib/api.ts`**

```ts
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type SkillOut = { name: string; slug: string };
export type GoalOut = { name: string; slug: string };
export type CourseOut = {
  id: string;
  title: string;
  url: string;
  difficulty: string | null;
  duration_minutes: number | null;
};
export type PathStep = { skill: SkillOut; courses: CourseOut[] };
export type PathResponse = { goal: GoalOut; steps: PathStep[] };
export type CourseListItem = CourseOut & { skills: SkillOut[] };
export type CourseDetail = CourseOut & {
  description: string | null;
  source_name: string;
  skills: SkillOut[];
};

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  return response.json();
}

export async function createPath(goalSlug: string): Promise<PathResponse> {
  const response = await fetch(`${API_BASE_URL}/paths`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goal_slug: goalSlug }),
  });
  return handleResponse<PathResponse>(response);
}

export async function listCourses(params: {
  search?: string;
  skill?: string;
  limit?: number;
  offset?: number;
}): Promise<{ courses: CourseListItem[]; total: number }> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.skill) query.set("skill", params.skill);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const response = await fetch(`${API_BASE_URL}/courses?${query.toString()}`);
  return handleResponse<{ courses: CourseListItem[]; total: number }>(response);
}

export async function getCourse(id: string): Promise<CourseDetail> {
  const response = await fetch(`${API_BASE_URL}/courses/${id}`);
  return handleResponse<CourseDetail>(response);
}
```

- [ ] **Step 2: Create `frontend/lib/useLocalPath.ts`**

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import type { GoalOut, PathResponse, PathStep } from "@/lib/api";

const STORAGE_KEY = "skillpath.currentPath";

export type StoredPath = {
  goal: GoalOut;
  steps: PathStep[];
  completedCourseIds: string[];
};

function readStoredPath(): StoredPath | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredPath;
  } catch {
    return null;
  }
}

function writeStoredPath(path: StoredPath | null) {
  if (typeof window === "undefined") return;
  if (path === null) {
    window.localStorage.removeItem(STORAGE_KEY);
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(path));
  }
}

export function useLocalPath() {
  const [path, setPath] = useState<StoredPath | null>(null);

  useEffect(() => {
    setPath(readStoredPath());
  }, []);

  const savePath = useCallback((newPath: PathResponse) => {
    const stored: StoredPath = { ...newPath, completedCourseIds: [] };
    writeStoredPath(stored);
    setPath(stored);
  }, []);

  const toggleCourseComplete = useCallback((courseId: string) => {
    setPath((current) => {
      if (!current) return current;
      const isComplete = current.completedCourseIds.includes(courseId);
      const completedCourseIds = isComplete
        ? current.completedCourseIds.filter((id) => id !== courseId)
        : [...current.completedCourseIds, courseId];
      const updated = { ...current, completedCourseIds };
      writeStoredPath(updated);
      return updated;
    });
  }, []);

  const isCourseComplete = useCallback(
    (courseId: string) => path?.completedCourseIds.includes(courseId) ?? false,
    [path]
  );

  const clearPath = useCallback(() => {
    writeStoredPath(null);
    setPath(null);
  }, []);

  return { path, savePath, toggleCourseComplete, isCourseComplete, clearPath };
}
```

- [ ] **Step 3: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds (these files aren't imported anywhere yet, but
must type-check standalone).

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/useLocalPath.ts
git commit -m "feat: add API client and local path/progress hook"
```

---

## Task 8: Onboarding screen (goal input)

Per `DESIGN.md`: single input, popular-goal chips, one primary CTA,
free-forever reassurance line.

**Files:**
- Create: `frontend/app/onboarding/page.tsx`

**Interfaces:**
- Consumes: `createPath` and `ApiError` (Task 7's `lib/api.ts`);
  `useLocalPath` → `savePath` (Task 7's `lib/useLocalPath.ts`).
- Produces: nothing consumed by later tasks (this is a leaf screen), but
  establishes the "one seeded goal" constraint: only `data-analyst` exists
  in the database this sprint (per `CLAUDE.md`'s schema section), so the
  popular-goal chip list is limited to that one real option — it links
  directly rather than pretending others exist.

- [ ] **Step 1: Create `frontend/app/onboarding/page.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, createPath } from "@/lib/api";
import { useLocalPath } from "@/lib/useLocalPath";

const POPULAR_GOALS = [{ label: "Data analyst", slug: "data-analyst" }];

export default function OnboardingPage() {
  const router = useRouter();
  const { savePath } = useLocalPath();
  const [goalSlug, setGoalSlug] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitGoal(slug: string) {
    setError(null);
    setIsSubmitting(true);
    try {
      const path = await createPath(slug);
      savePath(path);
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

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
      <h1 className="text-2xl font-bold">what do you want to learn?</h1>

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
          build my path
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

      <p className="text-sm text-muted">no credit card. no catch. ever.</p>
    </div>
  );
}
```

- [ ] **Step 2: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: with the backend running (`uvicorn backend.main:app --reload`
from the repo root) and `npm run dev` in `frontend/`, open
`http://localhost:3000/onboarding`, click the "Data analyst" chip, confirm
it redirects to `/` without an error.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/onboarding/page.tsx
git commit -m "feat: add onboarding goal-input screen"
```

---

## Task 9: Root page — landing (no path) + dashboard (path view)

Per `DESIGN.md` section 4/5: a first-time visitor with no saved path sees
the landing page; once a path exists in `localStorage`, the same route
(`/`) shows the dashboard instead. This is a client-side check, not two
routes, per the spec's Decision 3.

**Files:**
- Create: `frontend/components/Landing.tsx`
- Create: `frontend/components/Dashboard.tsx`
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `useLocalPath` (Task 7).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Create `frontend/components/Landing.tsx`**

```tsx
import Link from "next/link";

export function Landing() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center gap-8 px-4 py-16 text-center">
      <div className="flex flex-col gap-4">
        <h1 className="text-3xl font-bold md:text-4xl">
          you don&apos;t need money to learn something new.
        </h1>
        <p className="text-gray-600">
          SkillPath turns free content from across the web into a clear,
          step-by-step path — so you always know what to do next.
        </p>
      </div>

      <Link
        href="/onboarding"
        className="rounded bg-accent px-6 py-3 font-medium text-white"
      >
        start for free
      </Link>

      <div className="grid grid-cols-1 gap-6 text-left md:grid-cols-3">
        <div>
          <p className="font-medium">1. pick a goal</p>
          <p className="text-sm text-gray-600">tell us what you want to learn.</p>
        </div>
        <div>
          <p className="font-medium">2. get your path</p>
          <p className="text-sm text-gray-600">
            an ordered sequence of free courses, built for you.
          </p>
        </div>
        <div>
          <p className="font-medium">3. track progress</p>
          <p className="text-sm text-gray-600">
            mark courses complete as you go.
          </p>
        </div>
      </div>

      <div className="flex gap-4 text-sm text-success">
        <span>$0 cost</span>
        <span>100% free</span>
        <span>any skill</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/Dashboard.tsx`**

```tsx
import Link from "next/link";
import type { StoredPath } from "@/lib/useLocalPath";

export function Dashboard({
  path,
  isCourseComplete,
}: {
  path: StoredPath;
  isCourseComplete: (courseId: string) => boolean;
}) {
  const allCourses = path.steps.flatMap((step) => step.courses);
  const completedCount = allCourses.filter((c) => isCourseComplete(c.id)).length;
  const totalCount = allCourses.length;
  const progressPercent = totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-xl font-bold">{path.goal.name}</h1>
        <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
          <div
            className="h-2 rounded-full bg-accent"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="flex gap-4 text-sm">
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {totalCount - completedCount} steps left
        </span>
        <span className="rounded-full bg-success/10 px-3 py-1 text-success">
          free
        </span>
      </div>

      <ol className="flex flex-col divide-y divide-gray-200 border-y border-gray-200">
        {path.steps.map((step, index) => {
          const stepComplete =
            step.courses.length > 0 && step.courses.every((c) => isCourseComplete(c.id));
          return (
            <li key={step.skill.slug} className="flex flex-col gap-2 py-4">
              <div className="flex items-center gap-3">
                <span
                  className={
                    stepComplete
                      ? "flex h-6 w-6 items-center justify-center rounded-full bg-success text-white"
                      : "flex h-6 w-6 items-center justify-center rounded-full border border-gray-400 text-gray-600"
                  }
                >
                  {index + 1}
                </span>
                <span className="font-medium">{step.skill.name}</span>
              </div>
              <div className="flex flex-col gap-1 pl-9">
                {step.courses.length === 0 && (
                  <span className="text-sm text-muted">no courses yet for this step</span>
                )}
                {step.courses.map((course) => (
                  <Link
                    key={course.id}
                    href={`/course/${course.id}`}
                    className="text-sm text-gray-900 underline"
                  >
                    {course.title}
                  </Link>
                ))}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
```

- [ ] **Step 3: Wire both into `frontend/app/page.tsx`**

```tsx
"use client";

import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useLocalPath } from "@/lib/useLocalPath";

export default function HomePage() {
  const { path, isCourseComplete } = useLocalPath();

  if (!path) {
    return <Landing />;
  }

  return <Dashboard path={path} isCourseComplete={isCourseComplete} />;
}
```

- [ ] **Step 4: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, open `http://localhost:3000` with no path
saved — see the landing page. Go through `/onboarding`, confirm `/` now
shows the dashboard with the data-analyst path's 4 steps.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/Landing.tsx frontend/components/Dashboard.tsx frontend/app/page.tsx
git commit -m "feat: add landing page and dashboard path view"
```

---

## Task 10: Search/browse screen

Per `DESIGN.md` section 5: search bar, bordered-row results list, each
tagged Free. (The "Trending now"/"Most sought-after" sections in DESIGN.md
are static editorial content per section 9's data-grounding note — out of
scope for this sprint's backend, which only has ingested course data; the
search/filter functionality itself is in scope.)

**Files:**
- Create: `frontend/app/browse/page.tsx`

**Interfaces:**
- Consumes: `listCourses` (Task 7's `lib/api.ts`).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Create `frontend/app/browse/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { type CourseListItem, listCourses } from "@/lib/api";

export default function BrowsePage() {
  const [search, setSearch] = useState("");
  const [courses, setCourses] = useState<CourseListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setIsLoading(true);
      setError(null);
      listCourses({ search: search || undefined, limit: 20 })
        .then((result) => setCourses(result.courses))
        .catch(() => setError("Couldn't load courses. Please try again."))
        .finally(() => setIsLoading(false));
    }, 300);
    return () => clearTimeout(timeout);
  }, [search]);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="search courses"
        className="rounded border border-gray-300 px-4 py-3 text-base"
      />

      {isLoading && <p className="text-sm text-muted">loading...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <ul className="flex flex-col divide-y divide-gray-200 border-y border-gray-200">
        {courses.map((course) => (
          <li key={course.id} className="py-4">
            <Link href={`/course/${course.id}`} className="flex flex-col gap-1">
              <span className="font-medium">{course.title}</span>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-success/10 px-2 py-1 text-success">
                  free
                </span>
                {course.difficulty && (
                  <span className="rounded-full bg-gray-100 px-2 py-1 text-gray-700">
                    {course.difficulty}
                  </span>
                )}
                {course.skills.map((skill) => (
                  <span key={skill.slug} className="rounded-full bg-gray-100 px-2 py-1 text-gray-700">
                    {skill.name}
                  </span>
                ))}
              </div>
            </Link>
          </li>
        ))}
      </ul>

      {!isLoading && courses.length === 0 && (
        <p className="text-sm text-muted">no courses found.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: `npm run dev`, open `http://localhost:3000/browse`, confirm
courses load, typing in the search box filters the list.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/browse/page.tsx
git commit -m "feat: add search/browse screen"
```

---

## Task 11: Course detail screen

Per `DESIGN.md` section 5: thumbnail placeholder, title, source/duration/
difficulty meta, skill tags, description, "why this is in your path"
callout, Start course / Mark as complete actions, Up next row.

**Files:**
- Create: `frontend/app/course/[id]/page.tsx`

**Interfaces:**
- Consumes: `getCourse`, `ApiError` (Task 7's `lib/api.ts`); `useLocalPath`
  → `path`, `toggleCourseComplete`, `isCourseComplete` (Task 7's
  `lib/useLocalPath.ts`).
- Produces: nothing consumed by later tasks.

- [ ] **Step 1: Create `frontend/app/course/[id]/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { type CourseDetail, getCourse } from "@/lib/api";
import { useLocalPath } from "@/lib/useLocalPath";

export default function CourseDetailPage() {
  const params = useParams<{ id: string }>();
  const { path, toggleCourseComplete, isCourseComplete } = useLocalPath();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCourse(params.id)
      .then(setCourse)
      .catch(() => setError("Course not found."));
  }, [params.id]);

  if (error) {
    return <p className="px-4 py-8 text-sm text-red-600">{error}</p>;
  }

  if (!course) {
    return <p className="px-4 py-8 text-sm text-muted">loading...</p>;
  }

  const stepIndex = path?.steps.findIndex((step) =>
    step.courses.some((c) => c.id === course.id)
  );
  const step = stepIndex !== undefined && stepIndex >= 0 ? path?.steps[stepIndex] : undefined;
  const nextCourseInStep =
    step && stepIndex !== undefined
      ? step.courses[step.courses.findIndex((c) => c.id === course.id) + 1]
      : undefined;

  const complete = isCourseComplete(course.id);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <div className="aspect-video w-full rounded bg-gray-100" />

      <div>
        <h1 className="text-xl font-bold">{course.title}</h1>
        <p className="text-sm text-gray-600">
          {course.source_name}
          {course.duration_minutes ? ` · ${course.duration_minutes} min` : ""}
          {course.difficulty ? ` · ${course.difficulty}` : ""}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {course.skills.map((skill) => (
          <span key={skill.slug} className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700">
            {skill.name}
          </span>
        ))}
      </div>

      {course.description && <p className="text-sm text-gray-700">{course.description}</p>}

      {step && stepIndex !== undefined && (
        <p className="rounded border border-accent/30 bg-accent/5 px-4 py-3 text-sm">
          Step {stepIndex + 1} of {path!.steps.length} in your {path!.goal.name} path —
          builds your {step.skill.name} skills.
        </p>
      )}

      <div className="flex flex-col gap-3 md:flex-row">
        <a
          href={course.url}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-accent px-4 py-3 text-center font-medium text-white"
        >
          start course
        </a>
        <button
          onClick={() => toggleCourseComplete(course.id)}
          className="rounded border border-gray-300 px-4 py-3 font-medium"
        >
          {complete ? "completed" : "mark as complete"}
        </button>
      </div>

      {nextCourseInStep && (
        <Link href={`/course/${nextCourseInStep.id}`} className="text-sm underline">
          up next: {nextCourseInStep.title}
        </Link>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds.

Manual check: from the dashboard (with a saved path), click a course link,
confirm the detail screen shows the "Step X of Y" callout and "mark as
complete" toggles, then reflects on the dashboard's progress bar.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/course/
git commit -m "feat: add course detail screen"
```

---

## Task 12: Profile screen

Per `DESIGN.md` section 5: quick stats (courses done, hours learned, day
streak), list of all paths at real completion states, badges row. This
sprint only ever stores one path in `localStorage` (Decision 1 in the
spec — no multi-path history), so "list of all paths" degrades to
"the current path, if any" — shown honestly rather than faked.

**Files:**
- Create: `frontend/app/profile/page.tsx`

**Interfaces:**
- Consumes: `useLocalPath` → `path`, `isCourseComplete` (Task 7's
  `lib/useLocalPath.ts`).
- Produces: nothing consumed by later tasks. This is the last task in the
  plan.

- [ ] **Step 1: Create `frontend/app/profile/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useLocalPath } from "@/lib/useLocalPath";

export default function ProfilePage() {
  const { path, isCourseComplete } = useLocalPath();

  const allCourses = path?.steps.flatMap((step) => step.courses) ?? [];
  const completedCount = allCourses.filter((c) => isCourseComplete(c.id)).length;
  const totalMinutes = allCourses
    .filter((c) => isCourseComplete(c.id))
    .reduce((sum, c) => sum + (c.duration_minutes ?? 0), 0);
  const hoursLearned = Math.round(totalMinutes / 60);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-8">
      <h1 className="text-xl font-bold">your progress</h1>

      <div className="flex gap-4 text-sm">
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {completedCount} courses done
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1">
          {hoursLearned} hours learned
        </span>
      </div>

      <div>
        <h2 className="mb-2 font-medium">your paths</h2>
        {!path && (
          <p className="text-sm text-muted">
            no path started yet.{" "}
            <Link href="/onboarding" className="underline">
              set a goal
            </Link>
            .
          </p>
        )}
        {path && (
          <Link
            href="/"
            className="flex items-center justify-between border-y border-gray-200 py-3"
          >
            <span>{path.goal.name}</span>
            <span className="text-sm text-muted">
              {completedCount}/{allCourses.length} complete
            </span>
          </Link>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify it builds**

Run: `cd frontend && npm run build`
Expected: build succeeds. This completes Sprint 3's frontend build — full
manual check: with the backend running, walk through
onboarding → dashboard → course detail (mark complete) → profile (stats
reflect the completed course) → browse.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/profile/page.tsx
git commit -m "feat: add profile/progress screen"
```

---

## Post-plan note

Login/signup (`DESIGN.md`'s 7th screen) is intentionally not a task here —
it's Sprint 4 scope per the roadmap in `CLAUDE.md`, since it needs real
auth to be more than a static form. When Sprint 4 is scoped, it will also
need to decide how `localStorage`'s `StoredPath` migrates to
server-persisted progress once accounts exist.
