# Sprint 2 — Backend & Recommendation Logic

**Date:** 2026-09-06
**Status:** Approved, ready for implementation planning

## Purpose

Sprint 1 built the ingestion pipeline (YouTube → `courses` table) and confirmed a
working end-to-end run. Sprint 2 adds the FastAPI backend layer and the
rule-based recommendation logic described in the project roadmap: given a
skill goal, return an ordered learning path of courses.

## Scope

In scope:
- A `POST /paths` endpoint that takes a goal and returns an ordered,
  multi-skill learning path.
- A new `goals` / `goal_skills` schema (migration `002_goals.sql`) mapping a
  goal to an ordered sequence of skills.
- Extending `scripts/ingest_youtube.py` to populate `courses.difficulty` and
  `course_skills` (currently never written), via a keyword heuristic and an
  explicit `--skill` CLI argument.
- Manual seed data for 1-2 example goals to exercise the endpoint.
- Integration tests against the real local Postgres instance.

Out of scope (deferred to later sprints per the existing roadmap):
- `users` / `user_goals` — goal authoring UI or user-submitted goals.
- Course browsing/listing endpoints, skills listing endpoint, ingestion
  trigger/status endpoints — only the path-generation endpoint is built this
  sprint.
- Prerequisite graphs between individual courses (only skill-level ordering
  via `goal_skills.step_order` and difficulty-tier ordering within a skill).
- Non-flat relevance scoring (keyword-match-strength scoring, view-count
  weighting, etc.) — `course_skills.relevance_score` is set to a flat `1.0`
  by the ingestion heuristic this sprint.
- Authentication — no auth exists yet in the project; the endpoint is open.

## Architecture

New `backend/` FastAPI app, separate from `scripts/`:

```
backend/
  main.py          # FastAPI app, mounts routers
  db.py            # psycopg connection helper (same DATABASE_URL pattern as scripts/)
  routers/
    paths.py       # POST /paths
  queries.py       # raw SQL functions: get_goal, get_goal_skills, get_courses_for_skill
```

Runs via `uvicorn backend.main:app --reload`. Uses the same `.env` /
`DATABASE_URL` as the ingestion scripts. New dependencies: `fastapi`,
`uvicorn` (added to `requirements.txt`).

**Data access approach:** raw SQL via `psycopg`, matching the style already
used in `scripts/ingest_youtube.py` and `scripts/check_db.py`. No ORM.
Rationale: the schema is still small (7 tables after this sprint's
migration), and introducing an ORM now would mean two different ways of
talking to Postgres in the same repo (hand-written migrations +
`psycopg` in scripts, vs. ORM models + a second migration tool). Staying
raw-SQL keeps the pipeline and the API consistent.

## Schema changes — `migrations/002_goals.sql`

```sql
CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE goal_skills (
    goal_id UUID REFERENCES goals(id) ON DELETE CASCADE,
    skill_id UUID REFERENCES skills(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    PRIMARY KEY (goal_id, skill_id)
);
```

`step_order` fixes the sequence of skills within a path (e.g. SQL before
Python before statistics). Mirrors the existing `course_skills`
many-to-many pattern and the UUID/FK conventions already established in
`migrations/001_initial_schema.sql`.

Seed data (a plain SQL insert, not a script) creates 1-2 example goals —
e.g. `data-analyst` → SQL, Python, statistics — so the endpoint has real
data to return while building and testing this sprint. A real
goal-authoring path stays out of scope, consistent with the roadmap
already deferring `users` / `user_goals` to a later sprint.

## Ingestion changes — `scripts/ingest_youtube.py`

New required `--skill` argument ties an ingestion run's topic to a skill
slug explicitly (one run = one topic = one skill, for now):

```
python scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql --max-results 25
```

**Difficulty heuristic** — keyword match against the video title
(case-insensitive):
- Contains `beginner`, `intro`, `basics`, `101`, or `for beginners` →
  `beginner`
- Contains `advanced`, `deep dive`, `master`, or `expert` → `advanced`
- Otherwise → `intermediate`

Changes to `upsert_course`: add `difficulty` to the `INSERT` /
`ON CONFLICT ... DO UPDATE` (the column already exists in the schema but
has never been populated).

After a course is upserted, `get_or_create_skill(conn, skill_slug)` runs,
then a `course_skills` row is upserted: `(course_id, skill_id,
relevance_score)` with a flat `relevance_score = 1.0`, `ON CONFLICT DO
NOTHING`.

Rows ingested before this change (Sprint 1's 25 "SQL for beginners"
videos) will have `difficulty = NULL` and no `course_skills` row until
re-ingested with `--skill sql`.

## `POST /paths` — request/response & ordering

Request:
```json
{"goal_slug": "data-analyst"}
```

Flow:
1. `SELECT id, name, slug FROM goals WHERE slug = %s` — not found → `404
   {"detail": "goal not found"}`.
2. `SELECT skill_id, step_order, name, slug FROM goal_skills JOIN skills
   ... ORDER BY step_order` — builds the ordered skill sequence for the
   goal.
3. For each skill, fetch its courses:
   ```sql
   SELECT c.id, c.title, c.url, c.difficulty, c.duration_minutes, cs.relevance_score
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
   ```
   `duration_minutes ASC` is the tiebreak under the current flat
   `relevance_score` — the shorter course surfaces first within a tier.
   `ELSE 3` pushes untagged-difficulty courses (e.g. rows ingested before
   this sprint's heuristic existed) to the back instead of erroring.

Response:
```json
{
  "goal": {"name": "Data Analyst", "slug": "data-analyst"},
  "steps": [
    {
      "skill": {"name": "SQL", "slug": "sql"},
      "courses": [
        {"id": "...", "title": "...", "url": "...", "difficulty": "beginner", "duration_minutes": 12}
      ]
    }
  ]
}
```

A skill with zero matching courses is still included in `steps`, with
`"courses": []` — this is not an error. The path stays complete and
shows the full skill sequence, while flagging a content gap for that
skill.

## Error handling

- Unknown `goal_slug` → `404` with a `detail` message.
- A skill with no matching courses → `200`, empty `courses` list for that
  step (not an error — see above).
- Any other/unhandled DB error → falls through to FastAPI's default `500`.
  No custom error-handling middleware at this scope; the ingestion
  scripts' explicit try/except/log-and-raise pattern is not replicated
  here since the endpoint has no equivalent "run" record to update on
  failure.

## Testing

`tests/test_paths.py` using FastAPI's `TestClient`, run against the real
local `skillpath_db` — no mocked database, consistent with how the
pipeline is already verified via `scripts/check_db.py`. Covers:
- `POST /paths {"goal_slug": "data-analyst"}` → `200`, steps returned in
  the seeded `step_order`, courses within each step sorted by difficulty
  tier.
- Unknown `goal_slug` → `404`.
- A goal referencing a skill with zero ingested courses → `200`, that
  step's `courses` is `[]`.

## Open questions / explicitly deferred

None outstanding — all scope questions were resolved during design
(single-run-per-skill ingestion tagging, flat relevance scoring,
multi-skill goal mapping via a new table, raw-SQL data access). Anything
not listed under "Scope" above is deferred, not undecided.
