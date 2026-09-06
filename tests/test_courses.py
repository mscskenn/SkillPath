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
