from scripts.ingest_youtube import classify_difficulty


def test_classify_difficulty_beginner_keyword():
    assert classify_difficulty("SQL Tutorial for Beginners") == "beginner"


def test_classify_difficulty_advanced_keyword():
    assert classify_difficulty("Advanced SQL: Deep Dive into Window Functions") == "advanced"


def test_classify_difficulty_defaults_to_intermediate():
    assert classify_difficulty("Complete Python Course") == "intermediate"


def test_classify_difficulty_is_case_insensitive():
    assert classify_difficulty("PYTHON BASICS") == "beginner"
