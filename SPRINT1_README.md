# Sprint 1 setup

1. Copy `.env.example` to `.env` and fill in `YOUTUBE_API_KEY` once you have it.
2. Start Postgres: `docker compose up -d`
3. Apply the schema: `docker exec -i skillpath_db psql -U skillpath -d skillpath < migrations/001_initial_schema.sql`
4. Install Python deps: `pip install -r requirements.txt`
5. Run ingestion: `python scripts/ingest_youtube.py --topic "SQL for beginners"`
6. Verify it worked: `python scripts/check_db.py`

If step 5 fails, `check_db.py` will still show a `failed` row in ingestion_runs with an error message — that's the logging from `ingestion_runs` doing its job.
