from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_list_courses_returns_paginated_results():
    response = client.get("/courses", params={"limit": 5, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert "courses" in body and "total" in body
    assert len(body["courses"]) <= 5
    assert body["total"] >= len(body["courses"])


def test_list_courses_filters_by_skill():
    response = client.get("/courses", params={"skill": "sql", "limit": 50})
    body = response.json()
    assert len(body["courses"]) > 0
    for course in body["courses"]:
        assert any(s["slug"] == "sql" for s in course["skills"])


def test_list_courses_search_by_title():
    response = client.get("/courses", params={"search": "sql", "limit": 50})
    body = response.json()
    assert len(body["courses"]) > 0
    for course in body["courses"]:
        assert "sql" in course["title"].lower()


def test_list_courses_default_limit_is_20():
    response = client.get("/courses")
    body = response.json()
    assert len(body["courses"]) <= 20


def test_get_course_returns_detail():
    list_response = client.get("/courses", params={"skill": "sql", "limit": 1})
    courses = list_response.json()["courses"]
    assert courses, "expected at least one seeded 'sql' course - is the local DB seeded? see SPRINT1_README.md"
    course_id = courses[0]["id"]

    response = client.get(f"/courses/{course_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == course_id
    assert "description" in body
    assert "source_name" in body
    assert len(body["skills"]) > 0


def test_get_course_unknown_id_returns_404():
    response = client.get("/courses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "course not found"


def test_get_course_malformed_id_returns_422():
    response = client.get("/courses/not-a-uuid")
    assert response.status_code == 422
