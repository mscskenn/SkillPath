# Sprint 2 Backend & Recommendation Logic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `POST /paths` FastAPI endpoint that returns a difficulty-ordered, multi-skill learning path for a goal, backed by new `goals`/`goal_skills` schema and an ingestion heuristic that tags courses with difficulty and skill.

**Architecture:** Raw-SQL FastAPI app (`backend/`) alongside the existing `scripts/` pipeline, using the same `psycopg` + `.env`/`DATABASE_URL` pattern. `scripts/ingest_youtube.py` is extended to populate `courses.difficulty` and `course_skills` via a keyword heuristic and a new `--skill` CLI argument.

**Tech Stack:** Python, FastAPI, psycopg (raw SQL, no ORM), pytest, PostgreSQL 16 (Docker), `python-dotenv`.

**Spec:** `docs/superpowers/specs/2026-09-06-sprint2-backend-design.md`

## Global Constraints

- Data access is raw SQL via `psycopg` only — no ORM, no query builder.
- All DB access reuses the existing `.env` / `DATABASE_URL` pattern already used by `scripts/ingest_youtube.py` and `scripts/check_db.py`.
- Only one new endpoint this sprint: `POST /paths`. No course-listing, skills-listing, or ingestion-trigger endpoints.
- `course_skills.relevance_score` is set to a flat `1.0` by the ingestion heuristic — no keyword-strength scoring.
- Difficulty heuristic keyword lists (exact, case-insensitive substring match against the video title):
  - Beginner: `beginner`, `intro`, `basics`, `101`, `for beginners`
  - Advanced: `advanced`, `deep dive`, `master`, `expert`
  - Otherwise: `intermediate`
- Tests run against the real local `skillpath_db` Postgres instance — no mocked database.
- No authentication on the endpoint this sprint.

---

## File Structure

```
migrations/
  002_goals.sql                  # new: goals, goal_skills tables + seed data

scripts/
  ingest_youtube.py              # modified: difficulty heuristic, --skill arg, course_skills linking
tests/
  test_ingest_youtube.py         # new: unit tests for classify_difficulty
  test_paths.py                  # new: integration tests for POST /paths

backend/
  __init__.py                    # new: empty
  main.py                        # new: FastAPI app
  db.py                          # new: connection helper
  queries.py                     # new: raw SQL query functions
  routers/
    __init__.py                  # new: empty
    paths.py                     # new: POST /paths route + Pydantic models

requirements.txt                 # modified: add pytest, fastapi, uvicorn, httpx
```

---

### Task 1: Migration `002_goals.sql` — schema + seed data

**Files:**
- Create: `migrations/002_goals.sql`

**Interfaces:**
- Produces: tables `goals(id, name, slug)`, `goal_skills(goal_id, skill_id, step_order)`. Seeded rows: skills `sql`, `python`, `statistics`, `data-visualization`; goal `data-analyst` with `goal_skills` ordering `sql=1, python=2, statistics=3, data-visualization=4`. `data-visualization` is deliberately left without any ingested courses — later tasks rely on this to test the "skill with zero courses" path.

- [ ] **Step 1: Write the migration file**

```sql
-- Sprint 2 schema: goals, goal_skills
-- Seeds one example goal (data-analyst) so POST /paths has real data to
-- return during development and testing. "data-visualization" is seeded
-- with no ingested courses on purpose, to exercise the empty-courses path.

CREATE TABLE IF NOT EXISTS goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS goal_skills (
    goal_id UUID NOT NULL REFERENCES goals(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    PRIMARY KEY (goal_id, skill_id)
);

INSERT INTO skills (name, slug) VALUES
    ('SQL', 'sql'),
    ('Python', 'python'),
    ('Statistics', 'statistics'),
    ('Data Visualization', 'data-visualization')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO goals (name, slug) VALUES
    ('Data Analyst', 'data-analyst')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO goal_skills (goal_id, skill_id, step_order)
SELECT g.id, s.id, v.step_order
FROM (VALUES
    ('data-analyst', 'sql', 1),
    ('data-analyst', 'python', 2),
    ('data-analyst', 'statistics', 3),
    ('data-analyst', 'data-visualization', 4)
) AS v(goal_slug, skill_slug, step_order)
JOIN goals g ON g.slug = v.goal_slug
JOIN skills s ON s.slug = v.skill_slug
ON CONFLICT (goal_id, skill_id) DO NOTHING;
```

- [ ] **Step 2: Apply the migration**

Run: `docker exec -i skillpath_db psql -U skillpath -d skillpath < migrations/002_goals.sql`
Expected: `CREATE TABLE` x2, `INSERT 0 4`, `INSERT 0 1`, `INSERT 0 4` (no errors)

- [ ] **Step 3: Verify the seed data**

Run: `docker exec -i skillpath_db psql -U skillpath -d skillpath -c "SELECT g.slug, gs.step_order, sk.slug FROM goal_skills gs JOIN goals g ON g.id = gs.goal_id JOIN skills sk ON sk.id = gs.skill_id ORDER BY gs.step_order;"`
Expected: 4 rows, `data-analyst` paired with `sql`(1), `python`(2), `statistics`(3), `data-visualization`(4)

- [ ] **Step 4: Commit**

```bash
git add migrations/002_goals.sql
git commit -m "feat: add goals/goal_skills schema with seed data"
```

---

### Task 2: Difficulty heuristic — `classify_difficulty`

**Files:**
- Modify: `scripts/ingest_youtube.py` (add function near `parse_iso8601_duration_to_minutes`, around line 36)
- Test: `tests/test_ingest_youtube.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `classify_difficulty(title: str) -> str`, returning `"beginner"`, `"advanced"`, or `"intermediate"`. Task 3 imports and calls this.

- [ ] **Step 1: Add test/pytest/httpx/fastapi/uvicorn dependencies**

Add to `requirements.txt` (append after the existing three lines):

```
pytest==8.3.4
fastapi==0.115.6
uvicorn==0.34.0
httpx==0.28.1
```

Run: `venv/Scripts/python.exe -m pip install -r requirements.txt`
Expected: all four new packages install without errors

- [ ] **Step 2: Write the failing test**

Create `tests/test_ingest_youtube.py`:

```python
from scripts.ingest_youtube import classify_difficulty


def test_classify_difficulty_beginner_keyword():
    assert classify_difficulty("SQL Tutorial for Beginners") == "beginner"


def test_classify_difficulty_advanced_keyword():
    assert classify_difficulty("Advanced SQL: Deep Dive into Window Functions") == "advanced"


def test_classify_difficulty_defaults_to_intermediate():
    assert classify_difficulty("Complete Python Course") == "intermediate"


def test_classify_difficulty_is_case_insensitive():
    assert classify_difficulty("PYTHON BASICS") == "beginner"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `venv/Scripts/python.exe -m pytest tests/test_ingest_youtube.py -v`
Expected: FAIL with `ImportError: cannot import name 'classify_difficulty'`

- [ ] **Step 4: Add `classify_difficulty` to `scripts/ingest_youtube.py`**

Insert directly after `parse_iso8601_duration_to_minutes` (after line 36, before `def get_or_create_source`):

```python
BEGINNER_KEYWORDS = ("beginner", "intro", "basics", "101", "for beginners")
ADVANCED_KEYWORDS = ("advanced", "deep dive", "master", "expert")


def classify_difficulty(title: str) -> str:
    lowered = title.lower()
    if any(keyword in lowered for keyword in BEGINNER_KEYWORDS):
        return "beginner"
    if any(keyword in lowered for keyword in ADVANCED_KEYWORDS):
        return "advanced"
    return "intermediate"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `venv/Scripts/python.exe -m pytest tests/test_ingest_youtube.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add requirements.txt tests/test_ingest_youtube.py scripts/ingest_youtube.py
git commit -m "feat: add difficulty classification heuristic"
```

---

### Task 3: Skill tagging — `--skill` arg, `course_skills` linking, difficulty on courses

**Files:**
- Modify: `scripts/ingest_youtube.py`

**Interfaces:**
- Consumes: `classify_difficulty(title: str) -> str` from Task 2.
- Produces: `get_or_create_skill(conn, slug: str) -> str` (skill id), `link_course_skill(conn, course_id: str, skill_id: str) -> None`. `upsert_course` now returns the course id (`str`) instead of `None`. `run(topic: str, max_results: int, skill: str) -> None` (added `skill` parameter).

- [ ] **Step 1: Add `get_or_create_skill`**

Insert after `get_or_create_source` (after line 49):

```python
def get_or_create_skill(conn: psycopg.Connection, slug: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM skills WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if row:
            return row[0]
        name = slug.replace("-", " ").title()
        cur.execute(
            "INSERT INTO skills (name, slug) VALUES (%s, %s) RETURNING id",
            (name, slug),
        )
        return cur.fetchone()[0]
```

- [ ] **Step 2: Add `link_course_skill`**

Insert directly after `get_or_create_skill`:

```python
def link_course_skill(conn: psycopg.Connection, course_id: str, skill_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course_skills (course_id, skill_id, relevance_score)
            VALUES (%s, %s, 1.0)
            ON CONFLICT (course_id, skill_id) DO NOTHING
            """,
            (course_id, skill_id),
        )
```

- [ ] **Step 3: Update `upsert_course` to set difficulty and return the course id**

Replace the existing `upsert_course` function (lines 109-137) with:

```python
def upsert_course(conn: psycopg.Connection, source_id: str, video: dict) -> str:
    video_id = video["id"]
    snippet = video["snippet"]
    duration_minutes = parse_iso8601_duration_to_minutes(
        video["contentDetails"]["duration"]
    )
    difficulty = classify_difficulty(snippet["title"])
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO courses (
                source_id, external_id, title, url, description,
                duration_minutes, difficulty, published_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, external_id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                duration_minutes = EXCLUDED.duration_minutes,
                difficulty = EXCLUDED.difficulty
            RETURNING id
            """,
            (
                source_id,
                video_id,
                snippet["title"],
                f"https://www.youtube.com/watch?v={video_id}",
                snippet.get("description", ""),
                duration_minutes,
                difficulty,
                snippet.get("publishedAt"),
            ),
        )
        return cur.fetchone()[0]
```

- [ ] **Step 4: Wire `--skill` through `run()` and the argument parser**

Replace the `run` function (lines 140-164) with:

```python
def run(topic: str, max_results: int, skill: str) -> None:
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    database_url = os.environ.get("DATABASE_URL")
    if not api_key:
        sys.exit("YOUTUBE_API_KEY is not set. Add it to your .env file.")
    if not database_url:
        sys.exit("DATABASE_URL is not set. Add it to your .env file.")

    conn = psycopg.connect(database_url, autocommit=True)
    source_id = get_or_create_source(conn, name="youtube", source_type="video_platform")
    skill_id = get_or_create_skill(conn, skill)
    run_id = start_ingestion_run(conn, source_id)

    try:
        video_ids = search_video_ids(api_key, topic, max_results)
        videos = fetch_video_details(api_key, video_ids)
        for video in videos:
            course_id = upsert_course(conn, source_id, video)
            link_course_skill(conn, course_id, skill_id)
        finish_ingestion_run(conn, run_id, len(videos), status="success")
        print(f"Ingested {len(videos)} videos for topic '{topic}' (skill={skill}).")
    except Exception as exc:  # noqa: BLE001 - we want to log and fail loudly
        finish_ingestion_run(conn, run_id, 0, status="failed", error_message=str(exc))
        raise
    finally:
        conn.close()
```

Replace the `if __name__ == "__main__":` block (lines 167-172) with:

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest YouTube videos into the courses table.")
    parser.add_argument("--topic", required=True, help="Search topic, e.g. 'SQL for beginners'")
    parser.add_argument("--skill", required=True, help="Skill slug this topic maps to, e.g. 'sql'")
    parser.add_argument("--max-results", type=int, default=25, help="Max videos to pull (up to 50)")
    args = parser.parse_args()
    run(args.topic, args.max_results, args.skill)
```

- [ ] **Step 5: Re-ingest real data for `sql`, `python`, `statistics`**

Run each of the following (real YouTube API calls, real DB writes — leave `data-visualization` un-ingested on purpose, per the Task 1 note):

```bash
venv/Scripts/python.exe scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql --max-results 25
venv/Scripts/python.exe scripts/ingest_youtube.py --topic "Python for data analysis" --skill python --max-results 25
venv/Scripts/python.exe scripts/ingest_youtube.py --topic "Statistics for beginners" --skill statistics --max-results 25
```

Expected: each prints `Ingested 25 videos for topic '...' (skill=...).`

- [ ] **Step 6: Verify difficulty and skill tagging landed**

Run: `docker exec -i skillpath_db psql -U skillpath -d skillpath -c "SELECT sk.slug, COUNT(*) , COUNT(c.difficulty) FROM course_skills cs JOIN skills sk ON sk.id = cs.skill_id JOIN courses c ON c.id = cs.course_id GROUP BY sk.slug ORDER BY sk.slug;"`
Expected: 3 rows (`python`, `sql`, `statistics`), each with matching non-zero counts in both the total and the difficulty-not-null columns (confirms every linked course also has a difficulty set)

- [ ] **Step 7: Commit**

```bash
git add scripts/ingest_youtube.py
git commit -m "feat: tag ingested courses with difficulty and skill"
```

---

### Task 4: Backend connection helper and query functions

**Files:**
- Create: `backend/__init__.py` (empty)
- Create: `backend/db.py`
- Create: `backend/queries.py`

**Interfaces:**
- Produces: `get_connection() -> psycopg.Connection` (`backend/db.py`). `get_goal(conn, slug: str) -> dict | None`, `get_goal_skills(conn, goal_id: str) -> list[dict]`, `get_courses_for_skill(conn, skill_id: str) -> list[dict]` (`backend/queries.py`) — all `id` fields returned as `str`. Task 5 consumes all four.

- [ ] **Step 1: Create `backend/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/db.py`**

```python
import os

import psycopg
from dotenv import load_dotenv


def get_connection() -> psycopg.Connection:
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")
    return psycopg.connect(database_url)
```

- [ ] **Step 3: Create `backend/queries.py`**

```python
import psycopg


def get_goal(conn: psycopg.Connection, slug: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, slug FROM goals WHERE slug = %s", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        return {"id": str(row[0]), "name": row[1], "slug": row[2]}


def get_goal_skills(conn: psycopg.Connection, goal_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT sk.id, sk.name, sk.slug
            FROM goal_skills gs
            JOIN skills sk ON sk.id = gs.skill_id
            WHERE gs.goal_id = %s
            ORDER BY gs.step_order
            """,
            (goal_id,),
        )
        return [{"id": str(r[0]), "name": r[1], "slug": r[2]} for r in cur.fetchall()]


def get_courses_for_skill(conn: psycopg.Connection, skill_id: str) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.title, c.url, c.difficulty, c.duration_minutes
            FROM courses c
            JOIN course_skills cs ON cs.course_id = c.id
            WHERE cs.skill_id = %s
            ORDER BY
              CASE c.difficulty
                WHEN 'beginner' THEN 0
                WHEN 'intermediate' THEN 1
                WHEN 'advanced' THEN 2
                ELSE 3
              END,
              cs.relevance_score DESC,
              c.duration_minutes ASC
            """,
            (skill_id,),
        )
        return [
            {
                "id": str(r[0]),
                "title": r[1],
                "url": r[2],
                "difficulty": r[3],
                "duration_minutes": r[4],
            }
            for r in cur.fetchall()
        ]
```

- [ ] **Step 4: Sanity-check imports**

Run: `venv/Scripts/python.exe -c "from backend.db import get_connection; from backend.queries import get_goal, get_goal_skills, get_courses_for_skill; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add backend/__init__.py backend/db.py backend/queries.py
git commit -m "feat: add backend db connection helper and query functions"
```

---

### Task 5: `POST /paths` endpoint

**Files:**
- Create: `backend/routers/__init__.py` (empty)
- Create: `backend/routers/paths.py`
- Create: `backend/main.py`

**Interfaces:**
- Consumes: `get_connection` (`backend/db.py`), `get_goal`, `get_goal_skills`, `get_courses_for_skill` (`backend/queries.py`).
- Produces: FastAPI `app` object in `backend/main.py`, mounting `POST /paths`. Task 6 imports `backend.main.app`.

- [ ] **Step 1: Create `backend/routers/__init__.py`**

Empty file.

- [ ] **Step 2: Create `backend/routers/paths.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import get_connection
from backend.queries import get_courses_for_skill, get_goal, get_goal_skills

router = APIRouter()


class PathRequest(BaseModel):
    goal_slug: str


class CourseOut(BaseModel):
    id: str
    title: str
    url: str
    difficulty: str | None
    duration_minutes: int | None


class SkillOut(BaseModel):
    name: str
    slug: str


class GoalOut(BaseModel):
    name: str
    slug: str


class PathStep(BaseModel):
    skill: SkillOut
    courses: list[CourseOut]


class PathResponse(BaseModel):
    goal: GoalOut
    steps: list[PathStep]


@router.post("/paths", response_model=PathResponse)
def create_path(request: PathRequest) -> PathResponse:
    conn = get_connection()
    try:
        goal = get_goal(conn, request.goal_slug)
        if goal is None:
            raise HTTPException(status_code=404, detail="goal not found")

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

- [ ] **Step 3: Create `backend/main.py`**

```python
from fastapi import FastAPI

from backend.routers.paths import router

app = FastAPI(title="SkillPath API")
app.include_router(router)
```

- [ ] **Step 4: Manual smoke test with the dev server**

Run: `venv/Scripts/python.exe -m uvicorn backend.main:app --reload` (leave running), then in a second terminal:
`curl -X POST http://localhost:8000/paths -H "Content-Type: application/json" -d "{\"goal_slug\": \"data-analyst\"}"`
Expected: `200`, JSON body with `"goal": {"name": "Data Analyst", "slug": "data-analyst"}` and 4 `steps` (`sql`, `python`, `statistics`, `data-visualization`); the `data-visualization` step's `courses` is `[]`. Stop the server (Ctrl+C) after confirming.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/__init__.py backend/routers/paths.py backend/main.py
git commit -m "feat: add POST /paths endpoint"
```

---

### Task 6: Integration tests for `POST /paths`

**Files:**
- Create: `tests/test_paths.py`

**Interfaces:**
- Consumes: `app` from `backend.main`.

- [ ] **Step 1: Write the tests**

```python
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_create_path_returns_ordered_steps():
    response = client.post("/paths", json={"goal_slug": "data-analyst"})
    assert response.status_code == 200
    body = response.json()
    assert body["goal"] == {"name": "Data Analyst", "slug": "data-analyst"}
    skill_slugs = [step["skill"]["slug"] for step in body["steps"]]
    assert skill_slugs == ["sql", "python", "statistics", "data-visualization"]


def test_create_path_unknown_goal_returns_404():
    response = client.post("/paths", json={"goal_slug": "does-not-exist"})
    assert response.status_code == 404
    assert response.json()["detail"] == "goal not found"


def test_create_path_skill_with_no_courses_returns_empty_list():
    response = client.post("/paths", json={"goal_slug": "data-analyst"})
    body = response.json()
    data_viz_step = next(s for s in body["steps"] if s["skill"]["slug"] == "data-visualization")
    assert data_viz_step["courses"] == []


def test_create_path_courses_are_difficulty_ordered():
    response = client.post("/paths", json={"goal_slug": "data-analyst"})
    body = response.json()
    sql_step = next(s for s in body["steps"] if s["skill"]["slug"] == "sql")
    difficulty_rank = {"beginner": 0, "intermediate": 1, "advanced": 2, None: 3}
    ranks = [difficulty_rank[c["difficulty"]] for c in sql_step["courses"]]
    assert ranks == sorted(ranks)
```

- [ ] **Step 2: Run the tests**

Run: `venv/Scripts/python.exe -m pytest tests/test_paths.py -v`
Expected: 4 passed (requires Task 1's migration applied and Task 3's re-ingestion already done against the running `skillpath_db` container)

- [ ] **Step 3: Run the full test suite**

Run: `venv/Scripts/python.exe -m pytest -v`
Expected: all tests pass (Task 2's 4 unit tests + this task's 4 integration tests)

- [ ] **Step 4: Commit**

```bash
git add tests/test_paths.py
git commit -m "test: add integration tests for POST /paths"
```
