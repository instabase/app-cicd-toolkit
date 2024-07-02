"""Collection of unit tests for IB Helpers"""

from unittest.mock import patch
from ib_cicd.promote_sb_solution import (
    get_latest_flow_version,
    parse_dependencies_from_env,
    upload_icon,
    upload_package_json,
    get_version_from_ibsolution_path,
)
from tests.fixtures import (
    ib_host_url,
    ib_api_token,
)


@patch("ib_cicd.promote_sb_solution.list_directory")
def test_get_latest_flow_version(mock_list_dir, ib_host_url, ib_api_token):
    mock_list_dir.return_value = [
        "some/path/0.0.1.ibflow",
        "some/longer/path/4.0.30.ibflow",
        "some/path/0.0.3.ibflowbin",
    ]

    solution_path = "Test Space/Test Subspace/fs/Instabase Drive/My Solution"
    latest_version = get_latest_flow_version(solution_path, ib_host_url, ib_api_token)
    assert latest_version == "4.0.30"


def test_parse_dependencies_from_env():
    dependencies_str = "model_name==0.0.1,other_package==1.0.41"
    dependencies_dict = parse_dependencies_from_env(dependencies_str)
    assert dependencies_dict == {"model_name": "0.0.1", "other_package": "1.0.41"}

    dependencies_str = "model_name==0.0.1, other_package==1.0.41"
    dependencies_dict = parse_dependencies_from_env(dependencies_str)
    assert dependencies_dict == {"model_name": "0.0.1", "other_package": "1.0.41"}


@patch("ib_cicd.promote_sb_solution.upload_file")
def test_upload_icon(mock_upload_file, ib_host_url, ib_api_token):
    upload_icon(ib_host_url, ib_api_token, "some/path")
    calls = mock_upload_file.call_args_list
    assert len(calls) == 1
    assert calls[0][0][0] == "https://instbase-fake-testing-url.com"
    assert calls[0][0][1] == "fake-testing-token"
    assert isinstance(calls[0][0][2], str)


@patch("ib_cicd.promote_sb_solution.upload_file")
def test_upload_package_json(mock_upload_file, ib_host_url, ib_api_token):
    upload_package_json(
        "0.0.1", "flow_name", "solution_name", ib_host_url, ib_api_token, "some/path"
    )
    mock_upload_file.assert_called_with(
        "https://instbase-fake-testing-url.com",
        "fake-testing-token",
        "some/path",
        '{"name": "solution_name", "authors": ["INSTABASE"], "owner": "IB_DEPLOYED", "visibility": "PUBLIC", "version": "0.0.1", "short_description": "flow_name v0.0.1", "long_description": " ", "solution_type": "ibflowbin"}',
    )


def test_get_version_from_ibsolution_path():
    version = get_version_from_ibsolution_path(
        "path/to/ibsolution/file/solution_name-0.0.1.ibsolution"
    )
    assert version == "0.0.1"

    version = get_version_from_ibsolution_path(
        "path/to/ibsolution/file/0.0.1.ibsolution"
    )
    assert version == "0.0.1"

    version = get_version_from_ibsolution_path(
        "path/to/ibsolution/file/solution_name-50.0.1000.ibsolution"
    )
    assert version == "50.0.1000"
