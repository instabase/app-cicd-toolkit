"""Collection of unit tests for IB Helpers"""

import json
from unittest import mock
from requests.models import Response
from ib_cicd.ib_helpers import upload_file, compile_solution
from tests.fixtures import (
    ib_host_url,
    ib_api_token,
    _MOCK_IB_HOST_URL,
    _MOCK_AUTH_HEADERS,
)


@mock.patch("ib_cicd.ib_helpers.requests")
def test_compile_solution(mock_requests, ib_host_url, ib_api_token):
    # Arrange
    mocked_response = mock.Mock(spec=Response)
    mocked_response.status_code = 200
    mocked_response.content = json.dumps({"status": "OK"})
    mock_requests.post.return_value = mocked_response

    solution_path = "Test Space/Test Subspace/fs/Instabase Drive/My Solution"
    relative_flow_path = "Path to flow/flow.ibflow"
    compile_solution(ib_host_url, ib_api_token, solution_path, relative_flow_path)

    mock_requests.post.assert_called_with(
        "https://instbase-fake-testing-url.com/api/v1/flow_binary/compile/Test%20Space/Test%20Subspace/fs/Instabase%20Drive/My%20Solution",
        headers={"Authorization": "Bearer fake-testing-token"},
        data='{"binary_type": "Single Flow", "flow_project_root": "Test Space/Test Subspace/fs/Instabase Drive/My Solution/Path to flow", "predefined_binary_path": "Test Space/Test Subspace/fs/Instabase Drive/My Solution/Path to flow/flow.ibflowbin", "settings": {"flow_file": "flow.ibflow", "is_flow_v3": true}}',
        verify=False,
    )


@mock.patch("ib_cicd.ib_helpers.requests")
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
