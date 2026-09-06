from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_my_path_returns_404_when_no_goal_set(auth_headers):
    response = client.get("/me/path", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "no goal set"


def test_full_progress_flow(auth_headers):
    create_response = client.post(
        "/paths", json={"goal_slug": "data-analyst"}, headers=auth_headers
    )
    assert create_response.status_code == 200

    path_response = client.get("/me/path", headers=auth_headers)
    assert path_response.status_code == 200
    body = path_response.json()
    assert body["goal"] == {"name": "Data Analyst", "slug": "data-analyst"}
    assert body["completed_course_ids"] == []

    sql_step = next(s for s in body["steps"] if s["skill"]["slug"] == "sql")
    course_id = sql_step["courses"][0]["id"]

    toggle_response = client.post(
        "/me/progress", json={"course_id": course_id}, headers=auth_headers
    )
    assert toggle_response.status_code == 200
    assert toggle_response.json() == {"course_id": course_id, "completed": True}

    path_response_2 = client.get("/me/path", headers=auth_headers)
    assert course_id in path_response_2.json()["completed_course_ids"]

    toggle_again_response = client.post(
        "/me/progress", json={"course_id": course_id}, headers=auth_headers
    )
    assert toggle_again_response.json() == {"course_id": course_id, "completed": False}

    path_response_3 = client.get("/me/path", headers=auth_headers)
    assert course_id not in path_response_3.json()["completed_course_ids"]

    clear_response = client.delete("/me/path", headers=auth_headers)
    assert clear_response.status_code == 204

    path_response_4 = client.get("/me/path", headers=auth_headers)
    assert path_response_4.status_code == 404


def test_me_path_requires_auth():
    response = client.get("/me/path")
    assert response.status_code == 401


def test_me_progress_requires_auth():
    response = client.post(
        "/me/progress", json={"course_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 401
