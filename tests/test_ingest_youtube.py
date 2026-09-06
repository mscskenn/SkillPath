from scripts.ingest_youtube import (
    classify_difficulty,
    parse_iso8601_duration_to_minutes,
    redact_secret,
)


def test_classify_difficulty_beginner_keyword():
    assert classify_difficulty("SQL Tutorial for Beginners") == "beginner"


def test_classify_difficulty_advanced_keyword():
    assert classify_difficulty("Advanced SQL: Deep Dive into Window Functions") == "advanced"


def test_classify_difficulty_defaults_to_intermediate():
    assert classify_difficulty("Complete Python Course") == "intermediate"


def test_classify_difficulty_is_case_insensitive():
    assert classify_difficulty("PYTHON BASICS") == "beginner"


def test_parse_duration_hours_and_minutes():
    # Pre-existing behavior that must keep working.
    assert parse_iso8601_duration_to_minutes("PT1H30M") == 90


def test_parse_duration_seconds_only_rounds_up_to_one_minute():
    assert parse_iso8601_duration_to_minutes("PT45S") == 1


def test_parse_duration_with_day_component():
    # The bug: videos >= 24h use a day component YouTube's API emits as
    # e.g. "P1DT2H" (1 day, 2 hours). The old regex required a literal
    # "PT" prefix and had no day handling, so this failed to match and
    # silently returned 0 -- corrupting duration-based sort order.
    assert parse_iso8601_duration_to_minutes("P1DT2H") == 1560


def test_parse_duration_zero_duration_returns_none():
    # YouTube returns "P0D" for videos whose duration it hasn't
    # determined yet (e.g. an in-progress livestream), not for a
    # genuinely zero-length video. Treat it as unparseable rather than
    # silently recording 0 minutes.
    assert parse_iso8601_duration_to_minutes("P0D") is None


def test_parse_duration_malformed_string_returns_none():
    assert parse_iso8601_duration_to_minutes("GARBAGE") is None


def test_redact_secret_replaces_key_in_message():
    message = "403 Client Error: Forbidden for url: https://example.com/?key=SECRET123&q=sql"
    assert redact_secret(message, "SECRET123") == (
        "403 Client Error: Forbidden for url: https://example.com/?key=***&q=sql"
    )


def test_redact_secret_no_op_when_secret_missing():
    assert redact_secret("some message", None) == "some message"
    assert redact_secret("some message", "") == "some message"
