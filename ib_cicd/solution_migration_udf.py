from ib_cicd.ib_helpers import upload_file, publish_to_marketplace
from ib_cicd.migration_helpers import (
    read_file_through_api,
    download_ibsolution,
    get_dependencies_from_ibsolution,
    download_dependencies_from_dev_and_upload_to_prod,
)

import logging
import os
import json


def migrate_solution(
    source_ib_host,
    target_ib_host,
    source_api_token,
    target_api_token,
    solution_build_dir_path,
    target_ib_solution_folder,
    source_download_folder_dir=None,
    target_upload_folder_dir=None,
    **kwargs,
):
    """
    Function to migrate a solution from a source environment to a target environment

    The source environment already contains ibsolution and solution build directory, while the target environment will be
    where the solution gets migrated to

    :param source_ib_host: (str) IB host of source environment
    :param target_ib_host: (str) IB host of target environment
    :param source_api_token: (str) IB API token of source environment
    :param target_api_token: (str) IB API token of target environment
    :param solution_build_dir_path: (str) path to existing solution build directory on
    :param target_ib_solution_folder: (str) path to directory where ibsolution gets uploaded to on target environment
    :param source_download_folder_dir: (str) path to directory where temporary download folder will be created on source
                                             environment to download dependency ibsolutions from marketplace.
                                             Defaults to parent directory of the solution_build_dir_path
    :param target_upload_folder_dir: (str)   path to directory where temporary upload folder will be created on target
                                             environment to upload dependency ibsolutions from marketplace.
                                             Defaults to target_ib_solution_folder
    :param kwargs:
    :return:
    """
    # TODO: Compile build directory to an ibsolution if one doesn't already exist

    # TODO: Bring in something similar to flags from promote_solution

    # Set path to package.json from solution build directory
    package_json_path = os.path.join(solution_build_dir_path, "package.json")

    # Read package.json from IB
    read_response = read_file_through_api(
        source_ib_host, source_api_token, package_json_path
    )
    package = json.loads(read_response.content)

    # Set path for ibsolution file
    file_path = os.path.join(
        solution_build_dir_path, f'{package["name"]}-{package["version"]}.ibsolution'
    )

    # Download ibsolution from dev environment
    resp = download_ibsolution(source_ib_host, source_api_token, file_path)

    # Upload IB Solution to Prod
    solution_name = f'{package["name"]}-{package["version"]}.ibsolution'
    upload_path = os.path.join(target_ib_solution_folder, solution_name)
    upload_file(source_ib_host, target_api_token, upload_path, resp.content)

    # Get dependencies (dev packages + model solutions) from package.json
    requirements_dict = get_dependencies_from_ibsolution(
        source_ib_host, source_api_token, solution_build_dir_path
    )

    # Set up default download/upload folders if none are provided
    if not source_download_folder_dir:
        source_download_folder_dir = os.path.dirname(solution_build_dir_path)

    if not target_upload_folder_dir:
        target_upload_folder_dir = target_ib_solution_folder

    # Download dependencies from Dev and Upload to Prod (Creates folder in Dev and Prod with dependencies ibsolutions)
    uploaded_ibsolutions = download_dependencies_from_dev_and_upload_to_prod(
        source_ib_host,
        target_ib_host,
        source_api_token,
        target_api_token,
        source_download_folder_dir,
        target_upload_folder_dir,
        requirements_dict,
        use_clients=False,
        **kwargs,
    )

    # Publish ibsolutions to Prod marketplace
    for ib_solution_path in uploaded_ibsolutions:
        publish_resp = publish_to_marketplace(
            source_ib_host, source_api_token, ib_solution_path
        )
        logging.info(
            "Publish response for {}: {}".format(ib_solution_path, publish_resp)
        )

    return
