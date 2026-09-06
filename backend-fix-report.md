# Backend Audit Fix Report

Worktree: `C:/SkillPath-app/.claude/worktrees/audit-fixes` (branch `worktree-audit-fixes`)
Date: 2026-09-06

Baseline before any changes: 15/15 tests passing (`venv/Scripts/python.exe -m pytest -v`), `skillpath_db` Docker container healthy.

---

## Fix 1 (CRITICAL): YouTube API key leaks into the database and stdout

**File:** `scripts/ingest_youtube.py`

### The header-vs-query-string judgment call

The audit prompt suggested trying `headers={"X-goog-api-key": api_key}` instead of the `key` query
param, "if it works." I checked this before touching the request-building code: **YouTube Data API
v3 does not accept the API key via any request header.** The v3 API (unlike some newer Google APIs)
only recognizes `key` as a query parameter for API-key auth; there is no `X-goog-api-key` (or
equivalent) support for this API family. Forcing the key into a header would make every request fail
with 400/401, which is strictly worse than the leak we're fixing.

So I did **not** change `search_video_ids` / `fetch_video_details` to use headers. `key` stays in the
query string in both functions (required by the API), and instead I closed the leak at the two places
it can actually reach a human or storage:

1. **Persisted `error_message`**: previously `finish_ingestion_run(conn, run_id, 0, status="failed",
   error_message=str(exc))` stored the raw exception, and since `requests.raise_for_status()` embeds
   the full request URL (key included) in its message, a 403 (e.g. quota exhaustion, which is
   expected/routine, not exceptional) would write the live API key straight into the
   `ingestion_runs` table.
2. **stdout/traceback**: the old code did a bare `raise`, which re-raises the *original* exception
   object — its `str()` (with the key) is what Python prints in the traceback.

Both are now covered by a new `redact_secret(text, secret)` helper (pure function, unit tested) that
replaces every literal occurrence of the API key with `"***"`. In `run()`'s except block:

```python
sanitized_message = redact_secret(str(exc), api_key)
finish_ingestion_run(
    conn, run_id, records_ingested, status="failed", error_message=sanitized_message
)
raise RuntimeError(sanitized_message) from None
```

`from None` suppresses exception chaining, so the original (unredacted) exception object — and its
traceback text — never gets printed by Python's default traceback handler. Only the sanitized
`RuntimeError` propagates and prints. `redact_secret` treats falsy secrets (`None`, `""`) as a no-op,
which matters because replacing `""` in a string would otherwise insert `"***"` between every
character.

This is a **defense-in-depth backstop**, exactly as scoped in Fix 1: the *actual* leak vector was the
raw exception message, and it's now sanitized at both write sites (DB persistence and stdout) rather
than attempting (and failing) to keep the key out of the request itself.

### Tests added (`tests/test_ingest_youtube.py`)
- `test_redact_secret_replaces_key_in_message`
- `test_redact_secret_no_op_when_secret_missing`

---

## Fix 2 (CRITICAL): Video durations ≥24h parse to 0 minutes

**File:** `scripts/ingest_youtube.py`, function `parse_iso8601_duration_to_minutes`

### Root cause confirmed live in the DB

Before fixing anything I queried the local DB:

```sql
SELECT id, title, duration_minutes FROM courses WHERE duration_minutes = 0 OR duration_minutes IS NULL;
```

Result: **1 row** —

```
SQL Full Course for Beginners (30 Hours) — From Zero to Hero | duration_minutes = 0
```

This is the exact bug described in the audit: a 30-hour video recorded as `0` minutes, which sorts as
the shortest ("best") beginner SQL course in `get_courses_for_skill`'s `ORDER BY ... duration_minutes
ASC`.

### The fix

- Regex rewritten to add an optional day component and anchor the whole string:
  ```python
  ISO8601_DURATION_RE = re.compile(
      r"^P(?:(?P<days>\d+)D)?"
      r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
  )
  ```
- Matched with `re.fullmatch` (not `.match`), so trailing garbage no longer silently matches a prefix.
- `total_minutes` now includes `days * 1440`.
- **Unparseable input → `None`**, not `0`:
  - No regex match at all (`"GARBAGE"`) → `None`.
  - A match where every component is zero (`"P0D"`) → `None`. Rationale: YouTube's API returns
    `"P0D"` for a video whose duration it hasn't determined yet — most commonly an in-progress
    livestream/premiere — not for a genuinely zero-length video. Treating it as "unknown" (`None`,
    which the `duration_minutes` column already allows) is more honest than recording `0`, which
    would again sort as "shortest/best."
- **Preserved the original floor's intent** for genuinely short-but-nonzero durations: the pre-existing
  `max(total_minutes, 1)` existed (per `git log`, introduced in the same commit as the original parser)
  so a real video like `"PT10S"` (10 real seconds, rounds to 0 minutes under the `seconds >= 30`
  rounding rule) doesn't get recorded as `0` and confused with "unknown." That floor is now only
  applied *after* the all-zero/unparseable check, so it no longer masks the day-component bug or
  livestream placeholders — it only kicks in for durations that are genuinely nonzero but round down.

### Tests added (`tests/test_ingest_youtube.py`)
| Input | Expected | Covers |
|---|---|---|
| `PT1H30M` | `90` | pre-existing behavior, must not regress |
| `PT45S` | `1` | short duration, floor still applies |
| `P1DT2H` | `1560` | **the bug** — 1 day + 2 hours = 26h = 1560 min |
| `P0D` | `None` | livestream/zero-duration placeholder treated as unknown |
| `"GARBAGE"` | `None` | malformed input fails loudly (as `None`), doesn't crash |

### Backfill of existing bad data

I did **not** run a live re-ingestion. Checked `C:\SkillPath-app\.env` (found via `python-dotenv`'s
upward directory search from this worktree, since this worktree has no `.env` of its own) — it
contains what appears to be a **real, non-placeholder `YOUTUBE_API_KEY`**, not the
`your_key_here` placeholder from `.env.example`.

I chose not to consume that key / hit the live API / write to the shared local DB as a side effect of
an unattended bug-fix pass, since:
- It costs real YouTube API quota against a shared 10,000-unit/day budget.
- It's a data-mutating action beyond "fix the code," and the audit's own scope note says this is
  optional ("your realistic scope here is: fix the parser... flag that a re-ingestion should be run").

**Recommended next step for the user:** re-run ingestion for the `sql` skill (and any other
already-ingested skills/topics) to pick up the corrected parser:
```
venv/Scripts/python.exe scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql --max-results 25
```
This will `ON CONFLICT (source_id, external_id) DO UPDATE` the existing rows, including
`duration_minutes`, so the known-bad "30 Hours" row will self-correct without any manual SQL.

---

## Fix 3 (Important): Failed ingestion runs report `records_ingested = 0` incorrectly

**File:** `scripts/ingest_youtube.py`, function `run()`

Added a `records_ingested` counter initialized to `0` before the loop, incremented once per
successfully upserted+linked course inside the loop, and used in **both** the success and failure
`finish_ingestion_run` calls (previously the failure branch hardcoded `0`). Since the connection is
autocommit, any courses processed before a mid-run failure are already durably committed — the run
record now reflects that instead of understating it.

---

## Fix 4 (Important): CORS origin hardcoded

**Files:** `backend/main.py`, `.env.example`

```python
cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")
```
used in `allow_origins=cors_origins`. Added `CORS_ORIGINS=http://localhost:3000,http://localhost:3001`
to `.env.example`. `tests/test_cors.py` (pre-existing, unmodified) still passes since
`http://localhost:3000` remains in the default list.

---

## Fix 5 (Important): `course_id` not validated as UUID

**File:** `backend/routers/courses.py`

- Added `import uuid`.
- Changed `def get_course_endpoint(course_id: str)` → `def get_course_endpoint(course_id: uuid.UUID)`.
- FastAPI/Pydantic now rejects a malformed id with a `422` before the request handler body ever runs,
  so it never reaches `get_course_by_id`/Postgres.
- Body now passes `get_course_by_id(conn, str(course_id))` — `get_course_by_id`'s existing SQL/type
  contract expects a string; converting explicitly avoids relying on psycopg's UUID adapter matching
  the query function's undocumented expectations.

### Test added (`tests/test_courses.py`)
```python
def test_get_course_malformed_id_returns_422():
    response = client.get("/courses/not-a-uuid")
    assert response.status_code == 422
```

---

## Fix 6 (Important): plain `pytest` fails without `-m`

Created an empty `conftest.py` at the worktree root
(`C:\SkillPath-app\.claude\worktrees\audit-fixes\conftest.py`). Verified: `venv/Scripts/pytest.exe -v`
(direct invocation, no `-m`) now collects and passes all 23 tests — confirmed below.

---

## Fix 7 (Important): tests have no guard against empty/unseeded DB

**File:** `tests/test_courses.py`, `test_get_course_returns_detail`

```python
courses = list_response.json()["courses"]
assert courses, "expected at least one seeded 'sql' course - is the local DB seeded? see SPRINT1_README.md"
course_id = courses[0]["id"]
```

Checked the rest of `tests/test_courses.py` and `tests/test_paths.py` for other unguarded
list-indexing (`[0]`) patterns — this was the only one. `test_paths.py` uses `next(s for s in ...)`
generator lookups (not direct indexing), which weren't in scope per the audit's stated pattern and
weren't touched.

---

## Verification

### `venv/Scripts/python.exe -m pytest -v` — 23 passed
```
tests/test_cors.py::test_cors_allows_frontend_dev_origin PASSED
tests/test_courses.py::test_list_courses_returns_paginated_results PASSED
tests/test_courses.py::test_list_courses_filters_by_skill PASSED
tests/test_courses.py::test_list_courses_search_by_title PASSED
tests/test_courses.py::test_list_courses_default_limit_is_20 PASSED
tests/test_courses.py::test_get_course_returns_detail PASSED
tests/test_courses.py::test_get_course_unknown_id_returns_404 PASSED
tests/test_courses.py::test_get_course_malformed_id_returns_422 PASSED
tests/test_ingest_youtube.py::test_classify_difficulty_beginner_keyword PASSED
tests/test_ingest_youtube.py::test_classify_difficulty_advanced_keyword PASSED
tests/test_ingest_youtube.py::test_classify_difficulty_defaults_to_intermediate PASSED
tests/test_ingest_youtube.py::test_classify_difficulty_is_case_insensitive PASSED
tests/test_ingest_youtube.py::test_parse_duration_hours_and_minutes PASSED
tests/test_ingest_youtube.py::test_parse_duration_seconds_only_rounds_up_to_one_minute PASSED
tests/test_ingest_youtube.py::test_parse_duration_with_day_component PASSED
tests/test_ingest_youtube.py::test_parse_duration_zero_duration_returns_none PASSED
tests/test_ingest_youtube.py::test_parse_duration_malformed_string_returns_none PASSED
tests/test_ingest_youtube.py::test_redact_secret_replaces_key_in_message PASSED
tests/test_ingest_youtube.py::test_redact_secret_no_op_when_secret_missing PASSED
tests/test_paths.py::test_create_path_returns_ordered_steps PASSED
tests/test_paths.py::test_create_path_unknown_goal_returns_404 PASSED
tests/test_paths.py::test_create_path_skill_with_no_courses_returns_empty_list PASSED
tests/test_paths.py::test_create_path_courses_are_difficulty_ordered PASSED

======================= 23 passed, 26 warnings in 2.82s =======================
```
(warnings are pre-existing `anyio`/`asyncio.iscoroutinefunction` deprecation noise from
starlette/fastapi versions, unrelated to this fix pass)

### `venv/Scripts/pytest.exe -v` (plain, no `-m`) — 23 passed
Identical output/order to the above, confirming Fix 6:
```
======================= 23 passed, 26 warnings in 2.14s =======================
```

### `docker ps`
```
skillpath_db: Up 34 minutes (healthy)
```
Not touched; still healthy after all changes.

### Request-building re-check (Fix 1 backstop item #2)
Re-read `search_video_ids` and `fetch_video_details` after editing: `part`, `q`/`id`, `type`,
`maxResults` all remain as query params exactly as before — only the exception-handling path changed.
`key` was never moved out of `params` in either function, consistent with the "YouTube v3 requires
`key` as a query param" constraint.

---

## Concerns / notes for the user

1. **Fix 1 judgment call**: I did not implement the header-based key suggestion from the audit
   prompt — verified YouTube Data API v3 has no header-based key auth, so query-string + redaction
   was the only safe option. Flagging this explicitly since it was called out as something to verify
   rather than assume.
2. **Fix 2 backfill is not done** — only the parser is fixed for future runs. One row in the current
   DB (`SQL Full Course for Beginners (30 Hours)`, currently `duration_minutes = 0`) is still wrong
   until a re-ingestion is run. A real (non-placeholder) `YOUTUBE_API_KEY` exists in
   `C:\SkillPath-app\.env`, but I deliberately did not use it to avoid an unrequested live API call +
   DB mutation during this fix pass. Recommend running
   `scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql --max-results 25` (and similarly
   for `python`/`statistics`) to self-correct via the existing upsert logic.
3. Test suite grew from 15 to 23 (8 new tests: 6 for the duration parser + redact helper, 1 for the
   UUID 422 case, plus the existing-test guard change doesn't add a test but hardens one).
4. No production code outside the 7 fixes' listed files was touched. `docker-compose.yml` untouched,
   confirmed via `docker ps` that `skillpath_db` is unaffected.
