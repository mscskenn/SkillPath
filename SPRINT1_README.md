# Sprint 1 setup (historical — superseded by Sprint 4)

**As of Sprint 4, local dev no longer uses `docker compose up -d`/plain
Postgres or `migrations/*.sql`.** The local Supabase CLI stack
(`npx supabase start`) replaced both — see `scripts/setup-sprint4-dev.sh`
and `CLAUDE.md`'s "Sprint 4" section for current setup instructions.
This file is kept as a record of the original Sprint 1 workflow; steps
2-3 below describe infrastructure that has since been retired.

1. Copy `.env.example` to `.env` and fill in `YOUTUBE_API_KEY` once you have it.
2. ~~Start Postgres: `docker compose up -d`~~ (retired — use `npx supabase start`)
3. ~~Apply the schema: `docker exec -i skillpath_db psql -U skillpath -d skillpath < migrations/001_initial_schema.sql`~~ (retired — migrations live in `supabase/migrations/`, applied via `npx supabase db reset`)
4. Install Python deps: `pip install -r requirements.txt`
5. Run ingestion: `python scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql`
6. Verify it worked: `python scripts/check_db.py`

If step 5 fails, `check_db.py` will still show a `failed` row in ingestion_runs with an error message — that's the logging from `ingestion_runs` doing its job.
