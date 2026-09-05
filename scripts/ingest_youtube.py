"""
Pulls videos for a given topic from the YouTube Data API v3 and writes
normalized rows into the courses table. Logs every run to ingestion_runs
so failures and record counts are traceable, not silent.

Usage:
    python scripts/ingest_youtube.py --topic "SQL for beginners" --max-results 25
"""

import argparse
import os
import re
import sys
from datetime import datetime, timezone

import psycopg
import requests
from dotenv import load_dotenv

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
ISO8601_DURATION_RE = re.compile(
    r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?"
)


def parse_iso8601_duration_to_minutes(duration: str) -> int:
    match = ISO8601_DURATION_RE.match(duration)
    if not match:
        return 0
    parts = match.groupdict()
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)
    total_minutes = hours * 60 + minutes + (1 if seconds >= 30 else 0)
    return max(total_minutes, 1)


BEGINNER_KEYWORDS = ("beginner", "intro", "basics", "101", "for beginners")
ADVANCED_KEYWORDS = ("advanced", "deep dive", "master", "expert")


def classify_difficulty(title: str) -> str:
    lowered = title.lower()
    if any(keyword in lowered for keyword in BEGINNER_KEYWORDS):
        return "beginner"
    if any(keyword in lowered for keyword in ADVANCED_KEYWORDS):
        return "advanced"
    return "intermediate"


def get_or_create_source(conn: psycopg.Connection, name: str, source_type: str) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM sources WHERE name = %s", (name,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute(
            "INSERT INTO sources (name, type) VALUES (%s, %s) RETURNING id",
            (name, source_type),
        )
        return cur.fetchone()[0]


def start_ingestion_run(conn: psycopg.Connection, source_id: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion_runs (source_id, status)
            VALUES (%s, 'running')
            RETURNING id
            """,
            (source_id,),
        )
        return cur.fetchone()[0]


def finish_ingestion_run(
    conn: psycopg.Connection,
    run_id: str,
    records_ingested: int,
    status: str,
    error_message: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingestion_runs
            SET finished_at = %s, records_ingested = %s, status = %s, error_message = %s
            WHERE id = %s
            """,
            (datetime.now(timezone.utc), records_ingested, status, error_message, run_id),
        )


def search_video_ids(api_key: str, topic: str, max_results: int) -> list[str]:
    params = {
        "part": "snippet",
        "q": topic,
        "type": "video",
        "maxResults": min(max_results, 50),
        "key": api_key,
    }
    response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
    response.raise_for_status()
    return [item["id"]["videoId"] for item in response.json().get("items", [])]


def fetch_video_details(api_key: str, video_ids: list[str]) -> list[dict]:
    if not video_ids:
        return []
    params = {
        "part": "snippet,contentDetails",
        "id": ",".join(video_ids),
        "key": api_key,
    }
    response = requests.get(YOUTUBE_VIDEOS_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json().get("items", [])


def upsert_course(conn: psycopg.Connection, source_id: str, video: dict) -> None:
    video_id = video["id"]
    snippet = video["snippet"]
    duration_minutes = parse_iso8601_duration_to_minutes(
        video["contentDetails"]["duration"]
    )
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO courses (
                source_id, external_id, title, url, description,
                duration_minutes, published_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, external_id) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                duration_minutes = EXCLUDED.duration_minutes
            """,
            (
                source_id,
                video_id,
                snippet["title"],
                f"https://www.youtube.com/watch?v={video_id}",
                snippet.get("description", ""),
                duration_minutes,
                snippet.get("publishedAt"),
            ),
        )


def run(topic: str, max_results: int) -> None:
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY")
    database_url = os.environ.get("DATABASE_URL")
    if not api_key:
        sys.exit("YOUTUBE_API_KEY is not set. Add it to your .env file.")
    if not database_url:
        sys.exit("DATABASE_URL is not set. Add it to your .env file.")

    conn = psycopg.connect(database_url, autocommit=True)
    source_id = get_or_create_source(conn, name="youtube", source_type="video_platform")
    run_id = start_ingestion_run(conn, source_id)

    try:
        video_ids = search_video_ids(api_key, topic, max_results)
        videos = fetch_video_details(api_key, video_ids)
        for video in videos:
            upsert_course(conn, source_id, video)
        finish_ingestion_run(conn, run_id, len(videos), status="success")
        print(f"Ingested {len(videos)} videos for topic '{topic}'.")
    except Exception as exc:  # noqa: BLE001 - we want to log and fail loudly
        finish_ingestion_run(conn, run_id, 0, status="failed", error_message=str(exc))
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest YouTube videos into the courses table.")
    parser.add_argument("--topic", required=True, help="Search topic, e.g. 'SQL for beginners'")
    parser.add_argument("--max-results", type=int, default=25, help="Max videos to pull (up to 50)")
    args = parser.parse_args()
    run(args.topic, args.max_results)
