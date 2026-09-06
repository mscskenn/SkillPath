from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_cors_allows_frontend_dev_origin():
    response = client.get(
        "/courses",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
