import pytest

from tests.auth_helpers import create_test_user, delete_test_user, get_access_token

TEST_EMAIL = "sprint4-test-user@example.com"
TEST_PASSWORD = "testpassword123"


@pytest.fixture(scope="session")
def test_user_id():
    user_id = create_test_user(TEST_EMAIL, TEST_PASSWORD)
    yield user_id
    delete_test_user(user_id)


@pytest.fixture
def auth_headers(test_user_id):
    token = get_access_token(TEST_EMAIL, TEST_PASSWORD)
    return {"Authorization": f"Bearer {token}"}
