"""
Pulls videos for a given topic from the YouTube Data API v3 and writes
normalized rows into the courses table. Logs every run to ingestion_runs
so failures and record counts are traceable, not silent.

Usage:
    python scripts/ingest_youtube.py --topic "SQL for beginners" --skill sql --max-results 25
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
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_iso8601_duration_to_minutes(duration: str) -> int | None:
    """Convert a YouTube contentDetails.duration ISO-8601 string to minutes.

    Returns None when the string can't be parsed (garbage input) or when it
    parses but carries no actual duration (e.g. "P0D", which YouTube emits
    for an in-progress livestream/premiere rather than a genuinely
    zero-length video) -- None is more honest than 0 here, since 0 would
    otherwise sort as the "shortest" (best) beginner course.
    """
    match = ISO8601_DURATION_RE.fullmatch(duration)
    if not match:
        return None
    parts = match.groupdict()
    days = int(parts["days"] or 0)
    hours = int(parts["hours"] or 0)
    minutes = int(parts["minutes"] or 0)
    seconds = int(parts["seconds"] or 0)

    if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
        return None

    total_minutes = days * 1440 + hours * 60 + minutes + (1 if seconds >= 30 else 0)
    # A genuinely short-but-nonzero video (e.g. "PT10S") can round down to
    # 0 minutes; floor it to 1 so it isn't confused with the "unparseable"
    # None case above, while still sorting as the shortest course.
    return max(total_minutes, 1)


def redact_secret(text: str, secret: str | None) -> str:
    """Replace every occurrence of `secret` in `text` with "***".

    Used to keep API keys out of persisted error messages and stdout/
    tracebacks. A falsy secret is a no-op (an empty-string replace would
    otherwise insert "***" between every character of `text`).
    """
    if not secret:
        return text
    return text.replace(secret, "***")


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

    records_ingested = 0
    try:
        video_ids = search_video_ids(api_key, topic, max_results)
        videos = fetch_video_details(api_key, video_ids)
        for video in videos:
            course_id = upsert_course(conn, source_id, video)
            link_course_skill(conn, course_id, skill_id)
            records_ingested += 1
        finish_ingestion_run(conn, run_id, records_ingested, status="success")
        print(f"Ingested {records_ingested} videos for topic '{topic}' (skill={skill}).")
    except Exception as exc:  # noqa: BLE001 - we want to log and fail loudly
        # requests.raise_for_status() embeds the full request URL --
        # including the "key" query param -- in its exception message.
        # The YouTube Data API v3 only accepts the API key as a query
        # parameter (it does not support an auth header), so the key
        # can't simply be moved out of the URL. Instead, redact it from
        # the message before it's persisted to ingestion_runs.error_message
        # or reaches stdout, and record however many rows actually made it
        # in before the failure (autocommit means those rows are already
        # durable, so "failed" + 0 would otherwise understate the run).
        sanitized_message = redact_secret(str(exc), api_key)
        finish_ingestion_run(
            conn, run_id, records_ingested, status="failed", error_message=sanitized_message
        )
        raise RuntimeError(sanitized_message) from None
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest YouTube videos into the courses table.")
    parser.add_argument("--topic", required=True, help="Search topic, e.g. 'SQL for beginners'")
    parser.add_argument("--skill", required=True, help="Skill slug this topic maps to, e.g. 'sql'")
    parser.add_argument("--max-results", type=int, default=25, help="Max videos to pull (up to 50)")
    args = parser.parse_args()
    run(args.topic, args.max_results, args.skill)
