"""Collection of unit tests for IB Helpers"""
from unittest import mock
from requests.models import Response
from cicd.ib_helpers import upload_file
from tests.fixtures import ib_host_url, ib_api_token, _MOCK_IB_HOST_URL, _MOCK_AUTH_HEADERS


@mock.patch("cicd.ib_helpers.requests")
def test_upload_file(mock_requests, ib_host_url, ib_api_token):
    # Arrange
    mocked_response = mock.Mock(spec=Response)
    mocked_response.status_code = 204
    mock_requests.put.return_value = mocked_response
    upload_file_path = "Test Space/Test Subspace/fs/Instabase Drive"
    upload_file_data = "This is my test file data"

    # Act
    file_upload = upload_file(
        ib_host_url, ib_api_token, upload_file_path, upload_file_data
    )

    # Assert
    mock_requests.put.assert_called_with(
        f"{_MOCK_IB_HOST_URL}/api/v2/files/{upload_file_path}",
        headers=_MOCK_AUTH_HEADERS,
        data=upload_file_data,
        verify=False,
    )
    assert file_upload.status_code == 204
