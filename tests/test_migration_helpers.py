"""Collection of unit tests for IB Helpers"""
from unittest.mock import mock_open, patch, Mock
from requests.models import Response
from cicd.migration_helpers import download_ibsolution
from tests.fixtures import ib_host_url, ib_api_token, _MOCK_IB_HOST_URL, _MOCK_AUTH_HEADERS


@patch("cicd.ib_helpers.requests")
def test_download_ibsolution(mock_requests, ib_host_url, ib_api_token):
    mocked_response = Mock(spec=Response)
    mocked_response.status_code = 200
    mock_requests.get.return_value = mocked_response
    solution_path = "Test Space/Test Subspace/fs/Instabase Drive/solution/dummy_solution-0.0.1.ibsolution"

    resp = download_ibsolution(
        ib_host_url, ib_api_token, solution_path
    )

    mock_requests.get.assert_called_with(
        f"{_MOCK_IB_HOST_URL}/api/v2/files/{solution_path}",
        headers=_MOCK_AUTH_HEADERS,
        verify=False,
        params={'expect-node-type': 'file'}
    )
    assert resp.status_code == 200


@patch('cicd.migration_helpers.os.remove')
@patch("cicd.migration_helpers.ZipFile")
@patch('builtins.open', new_callable=mock_open)
@patch("cicd.ib_helpers.requests")
def test_download_ibsolution_and_unzip(mock_requests, mock_open, mock_zip, mock_remove, ib_host_url, ib_api_token):
    mocked_response = Mock(spec=Response)
    mocked_response.status_code = 200
    mock_requests.get.return_value = mocked_response
    solution_path = "Test Space/Test Subspace/fs/Instabase Drive/solution/dummy_solution-0.0.1.ibsolution"

    resp = download_ibsolution(
        ib_host_url, ib_api_token, solution_path, True, True
    )

    mock_zip.assert_called_with(
        'dummy_solution-0.0.1.zip',
        'r'
    )

    mock_remove.assert_called_with(
        'dummy_solution-0.0.1.zip'
    )

    mock_requests.get.assert_called_with(
        f"{_MOCK_IB_HOST_URL}/api/v2/files/{solution_path}",
        headers=_MOCK_AUTH_HEADERS,
        verify=False,
        params={'expect-node-type': 'file'}
    )
    assert resp.status_code == 200

