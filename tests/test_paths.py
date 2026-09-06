from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_create_path_returns_ordered_steps(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["goal"] == {"name": "Data Analyst", "slug": "data-analyst"}
    skill_slugs = [step["skill"]["slug"] for step in body["steps"]]
    assert skill_slugs == ["sql", "python", "statistics", "data-visualization"]


def test_create_path_unknown_goal_returns_404(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "does-not-exist"}, headers=auth_headers
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "goal not found"


def test_create_path_skill_with_no_courses_returns_empty_list(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    body = response.json()
    data_viz_step = next(
        s for s in body["steps"] if s["skill"]["slug"] == "data-visualization"
    )
    assert data_viz_step["courses"] == []


def test_create_path_courses_are_difficulty_ordered(auth_headers):
    response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    body = response.json()
    sql_step = next(s for s in body["steps"] if s["skill"]["slug"] == "sql")
    difficulty_rank = {"beginner": 0, "intermediate": 1, "advanced": 2, None: 3}
    assert len(sql_step["courses"]) > 0, "sql step should have ingested courses"
    ranks = [difficulty_rank[c["difficulty"]] for c in sql_step["courses"]]
    assert ranks == sorted(ranks)


def test_create_path_requires_auth():
    response = client.post("/paths", json={"goal_slug": "data-analyst"})
    assert response.status_code == 401
