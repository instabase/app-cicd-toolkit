import json

import os
import argparse
import re
import pathlib

from ib_cicd.ib_helpers import (
    upload_file,
    copy_file_within_ib,
    deploy_solution,
    package_solution,
    list_directory,
    read_file_through_api,
    compile_solution,
)
from ib_cicd.migration_helpers import (
    download_ibsolution,
    download_dependencies_from_dev_and_upload_to_prod,
    publish_dependencies,
)

from ib_cicd.promote_solution import (
    version_tuple,
    get_latest_ibsolution_path,
    set_output_version_github,
)
from dotenv import load_dotenv

load_dotenv()

TARGET_IB_API_TOKEN = os.environ.get("TARGET_IB_API_TOKEN")
SOURCE_IB_API_TOKEN = os.environ.get("SOURCE_IB_API_TOKEN")
TARGET_IB_HOST = os.environ.get("TARGET_IB_HOST")
SOURCE_IB_HOST = os.environ.get("SOURCE_IB_HOST")
SOLUTION_BUILDER_NAME = os.environ.get("SOLUTION_BUILDER_NAME")
FLOW_NAME = os.environ.get("FLOW_NAME")
WORKSPACE_DRIVE_PATH = os.environ.get("WORKSPACE_DRIVE_PATH")
TARGET_IB_PATH = os.environ.get("TARGET_IB_PATH")
SOURCE_WORKING_DIR = os.environ.get("SOURCE_WORKING_DIR")
DEPENDENCIES = os.environ.get("DEPENDENCIES")


def get_latest_flow_version(flow_path, ib_host, ib_token) -> str:
    """
    Iterates through the files in a folder to get the filename with the maximum version number
    :param flow_path: (string) IB path to directory where versioned flows are stored
    :param ib_host: (string) IB host URL (e.g. https://platform.instabase.com/)
    :param ib_token: (string) API token for IB environment
    :return: (string) latest version in directory in <major>.<minor>.<patch> format
    """
    latest_version = "0.0.0"
    try:
        paths = list_directory(ib_host, flow_path, ib_token)
    except Exception:
        return latest_version

    for path in paths:
        p = pathlib.Path(path)
        if re.fullmatch("[0-9]+.[0-9]+.[0-9]+", p.stem):
            if version_tuple(p.stem) > version_tuple(latest_version):
                latest_version = p.stem
    return latest_version


def get_sb_flow_path(solution_builder_name, flow_name, ib_root, ib_host, ib_token):
    """
    Iterates through flows in a solution builder project to return the path to the input flow name
    :param solution_builder_name: (string) name of solution builder project
    :param flow_name: (string) name of the flow
    :param ib_root: (string) path to the IB drive (e.g. hannahroiter/ci-cd/fs/Instabase Drive)
    :param ib_host: (string) IB host URL (e.g. https://platform.instabase.com/)
    :param ib_token: (string) API token for IB environment
    :return: (string) IB filesystem path to flow version
    """
    flows_path = os.path.join(
        ib_root, ".instabase_projects", solution_builder_name, "latest", "flows"
    )
    paths = list_directory(ib_host, flows_path, ib_token)
    for path in paths:
        read_response = read_file_through_api(
            ib_host, ib_token, os.path.join(path, "metadata.json")
        ).content
        metadata = json.loads(read_response)
        if metadata["name"] == flow_name:
            version = list_directory(ib_host, os.path.join(path, "versions"), ib_token)[
                0
            ]
            return version


def parse_dependencies_from_env(dependencies):
    """
    Generate a dictionary in the format {package or model name: version}
    :param dependencies: (string) versioned dependencies in the format model_name==0.0.1,package_name==0.1.4
    :return: (dict) dict representation of dependencies string
    """
    return {
        m.split("==")[0].strip(): m.split("==")[1].strip()
        for m in dependencies.split(",")
    }


def upload_icon(ib_host, ib_token, path, icon_path="icon.png"):
    """
    Uploads a local png file to the IB filesystem
    :param ib_host: (string) IB host URL (e.g. https://platform.instabase.com/)
    :param ib_token: (string) API token for IB environment
    :param path: (string) IB path to upload icon
    :param icon_path: (string) optional local path to read icon
    :return: Response object return from upload request
    """
    with open(icon_path, "rb") as image:
        f = image.read()
        b = bytearray(f)
    resp = upload_file(ib_host, ib_token, path, b)
    return resp


def upload_package_json(version, flow_name, solution_name, ib_host, ib_token, path):
    """
    Generates and uploads a package.json file to the IB filesystem
    :param version: (string) solution version in the format <major>.<minor>.<patch>
    :param flow_name: (string) name of the flow
    :param solution_name: (string) name of the solution builder project
    :param ib_host: (string) IB host URL (e.g. https://platform.instabase.com/)
    :param ib_token: (string) API token for IB environment
    :param path: (string) path on the IB filesystem to upload the package.json file
    :return: Response object return from upload request
    """
    package = {
        "name": solution_name,
        "authors": ["INSTABASE"],
        "owner": "IB_DEPLOYED",
        "visibility": "PUBLIC",
        "version": version,
        "short_description": f"{flow_name} v{version}",
        "long_description": " ",
        "solution_type": "ibflowbin",
    }
    resp = upload_file(ib_host, ib_token, path, json.dumps(package))
    return resp


def get_version_from_ibsolution_path(path):
    """

    :param path: (string) IB path to ibsolution file
    :return: (string) ibsolution version in format <major>.<minor>.<patch>
    """
    p = pathlib.Path(path)
    return p.stem.split("-")[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile_source_solution", action="store_true")
    parser.add_argument("--promote_solution_to_target", action="store_true")
    parser.add_argument("--deploy_source_solution", action="store_true")
    parser.add_argument("--deploy_target_solution", action="store_true")
    parser.add_argument("--upload_dependencies", action="store_true")
    parser.add_argument("--set_github_actions_env_var", action="store_true")
    parser.add_argument("--set_azure_devops_env_var", action="store_true")
    parser.add_argument("--download_ibsolution", action="store_true")
    parser.add_argument("--remote_flow", action="store_true")
    args = parser.parse_args()

    if args.compile_source_solution:
        flow_folder = get_sb_flow_path(
            SOLUTION_BUILDER_NAME,
            FLOW_NAME,
            WORKSPACE_DRIVE_PATH,
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
        )
        flow_path = os.path.join(flow_folder, "flow.ibflow")
        p = pathlib.Path(flow_path)
        flow_builds_dir = os.path.join(*p.parts[:-1], "builds")

        current_version = version_tuple(
            get_latest_flow_version(
                flow_builds_dir, SOURCE_IB_HOST, SOURCE_IB_API_TOKEN
            )
        )
        version = f"{current_version[0]}.{current_version[1]}.{current_version[2]+1}"
        compile_solution(
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            flow_path,
            solution_builder=True,
            solution_version=version,
        )

        solutions_dir = os.path.join(
            flow_builds_dir, "solutions", f"{SOLUTION_BUILDER_NAME}-{version}"
        )
        upload_icon(
            SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, os.path.join(solutions_dir, "icon.png")
        )

        package_path = os.path.join(solutions_dir, "package.json")
        upload_package_json(
            version,
            FLOW_NAME,
            SOLUTION_BUILDER_NAME,
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            package_path,
        )

        flow_binary_path = os.path.join(flow_builds_dir, f"{version}.ibflowbin")
        copy_file_within_ib(
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            flow_binary_path,
            os.path.join(solutions_dir, f"{version}.ibflowbin"),
        )

        package_solution(
            SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, solutions_dir, solutions_dir
        )
        ibsolution_name = f"{SOLUTION_BUILDER_NAME}-{version}.ibsolution"
        copy_file_within_ib(
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            os.path.join(solutions_dir, ibsolution_name),
            os.path.join(SOURCE_WORKING_DIR, ibsolution_name),
        )

    if args.deploy_source_solution or args.remote_flow:
        solution_path = get_latest_ibsolution_path(
            SOURCE_IB_API_TOKEN,
            SOURCE_IB_HOST,
            SOURCE_WORKING_DIR,
            SOLUTION_BUILDER_NAME,
        )
        deploy_solution(SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, solution_path)

    if args.promote_solution_to_target or args.remote_flow:
        solution_path = get_latest_ibsolution_path(
            SOURCE_IB_API_TOKEN,
            SOURCE_IB_HOST,
            SOURCE_WORKING_DIR,
            SOLUTION_BUILDER_NAME,
        )
        version = get_version_from_ibsolution_path(solution_path)

        resp = download_ibsolution(
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            solution_path,
            write_to_local=args.download_ibsolution,
        )
        target_path = os.path.join(
            TARGET_IB_PATH, f"{SOLUTION_BUILDER_NAME}-{version}.ibsolution"
        )
        upload_file(TARGET_IB_HOST, TARGET_IB_API_TOKEN, target_path, resp.content)

    if args.upload_dependencies or args.remote_flow:
        dependencies_dict = parse_dependencies_from_env(DEPENDENCIES)
        uploaded_ibsolutions = download_dependencies_from_dev_and_upload_to_prod(
            SOURCE_IB_HOST,
            TARGET_IB_HOST,
            SOURCE_IB_API_TOKEN,
            TARGET_IB_API_TOKEN,
            SOURCE_WORKING_DIR,
            TARGET_IB_PATH,
            dependencies_dict,
        )
        publish_dependencies(uploaded_ibsolutions, TARGET_IB_HOST, TARGET_IB_API_TOKEN)

    if args.deploy_target_solution or args.remote_flow:
        solution_path = get_latest_ibsolution_path(
            TARGET_IB_API_TOKEN, TARGET_IB_HOST, TARGET_IB_PATH, SOLUTION_BUILDER_NAME
        )
        deploy_solution(TARGET_IB_HOST, TARGET_IB_API_TOKEN, solution_path)

    if args.set_github_actions_env_var or args.set_azure_devops_env_var:
        latest_path = get_latest_ibsolution_path(
            TARGET_IB_API_TOKEN, TARGET_IB_HOST, TARGET_IB_PATH, SOLUTION_BUILDER_NAME
        )
        version = get_version_from_ibsolution_path(latest_path)

        if args.set_github_actions_env_var:
            set_output_version_github(version)
        else:
            print(f"##vso[task.setvariable variable=PACKAGE_VERSION;]{version}")


if __name__ == "__main__":
    main()
