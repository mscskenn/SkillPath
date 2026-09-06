import pytest

from tests.auth_helpers import create_test_user, delete_test_user, make_test_jwt


@pytest.fixture(scope="session")
def test_user_id():
    user_id = create_test_user("sprint4-test-user@example.com")
    yield user_id
    delete_test_user(user_id)


@pytest.fixture
def auth_headers(test_user_id):
    token = make_test_jwt(test_user_id)
    return {"Authorization": f"Bearer {token}"}
