"""
Quick sanity check: prints course counts by source and the most recent
ingestion runs, so you can verify ingestion worked without opening a DB client.

Usage:
    python scripts/check_db.py
"""

import os
import sys

import psycopg
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set. Add it to your .env file.")

    conn = psycopg.connect(database_url)
    with conn.cursor() as cur:
        print("Courses by source:")
        cur.execute(
            """
            SELECT s.name, COUNT(c.id)
            FROM sources s
            LEFT JOIN courses c ON c.source_id = s.id
            GROUP BY s.name
            ORDER BY s.name
            """
        )
        for name, count in cur.fetchall():
            print(f"  {name}: {count}")

        print("\nLast 5 ingestion runs:")
        cur.execute(
            """
            SELECT s.name, r.started_at, r.finished_at, r.records_ingested, r.status
            FROM ingestion_runs r
            JOIN sources s ON s.id = r.source_id
            ORDER BY r.started_at DESC
            LIMIT 5
            """
        )
        for name, started, finished, records, status in cur.fetchall():
            print(f"  [{status}] {name} started={started} finished={finished} records={records}")

    conn.close()


if __name__ == "__main__":
    main()
