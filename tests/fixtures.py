import pytest

_MOCK_IB_HOST_URL = "https://instbase-fake-testing-url.com"
_MOCK_API_TOKEN = "fake-testing-token"
_MOCK_AUTH_HEADERS = {"Authorization": f"Bearer {_MOCK_API_TOKEN}"}


@pytest.fixture
def ib_host_url():
    """Fixture for a mock testing IB host URL

    Returns:
        str: Mock IB host URL
    """
    return _MOCK_IB_HOST_URL


@pytest.fixture
def ib_api_token():
    """Fixture for a mock API token

    Returns:
        str: Mock API token
    """

    return _MOCK_API_TOKEN
