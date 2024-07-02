import time

import json
import pathlib
import os
import shutil
import argparse

from ib_cicd.ib_helpers import (
    unzip_files,
    upload_file,
    read_file_content_from_ib,
    copy_file_within_ib,
    publish_to_marketplace,
    delete_folder_or_file_from_ib,
    deploy_solution,
    list_directory,
)
from ib_cicd.migration_helpers import (
    download_ibsolution,
    compile_and_package_ib_solution,
    download_dependencies_from_dev_and_upload_to_prod,
    publish_dependencies,
)
from dotenv import load_dotenv

load_dotenv()

TARGET_IB_API_TOKEN = os.environ.get("TARGET_IB_API_TOKEN")
SOURCE_IB_API_TOKEN = os.environ.get("SOURCE_IB_API_TOKEN")

TARGET_IB_HOST = os.environ.get("TARGET_IB_HOST")
SOURCE_IB_HOST = os.environ.get("SOURCE_IB_HOST")
TARGET_IB_PATH = os.environ.get("TARGET_IB_PATH")
SOURCE_WORKING_DIR = os.environ.get("SOURCE_WORKING_DIR")
SOURCE_SOLUTION_DIR = os.environ.get("SOURCE_SOLUTION_DIR")
SOURCE_COMPILED_SOLUTIONS_PATH = os.environ.get("SOURCE_COMPILED_SOLUTIONS_PATH")
LOCAL_SOLUTION_DIR = os.environ.get("LOCAL_SOLUTION_DIR")
REL_FLOW_PATH = os.environ.get("REL_FLOW_PATH")

TARGET_FILES_API = os.path.join(*[TARGET_IB_HOST, "api/v2", "files"])
SOURCE_FILES_API = os.path.join(*[SOURCE_IB_HOST, "api/v2", "files"])


def parse_dependencies(package_dependencies):
    models = {
        m.split("==")[0].strip(): m.split("==")[1].strip()
        for m in package_dependencies.get("models", [])
    }
    packages = {
        p.split("==")[0].strip(): p.split("==")[1].strip()
        for p in package_dependencies.get("dev_exchange_packages", [])
    }
    return {**packages, **models}


def read_local_package_json(directory_name, package_path=None):
    package_path = package_path if package_path else f"{directory_name}/package.json"
    with open(package_path) as fp:
        package = json.load(fp)
    return package


def upload_zip_to_instabase():
    shutil.make_archive("solution", "zip", LOCAL_SOLUTION_DIR)

    path_to_upload = os.path.join(*[TARGET_IB_PATH, LOCAL_SOLUTION_DIR + ".zip"])

    upload_data = open("solution.zip", "rb")
    resp = upload_file(TARGET_IB_HOST, TARGET_IB_API_TOKEN, path_to_upload, upload_data)
    return resp


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


def get_latest_ibsolution_path(api_token, ib_host, solution_path, solution_name=None):
    paths = list_directory(ib_host, solution_path, api_token)
    paths = [p for p in paths if p.endswith(".ibsolution")]
    if len(paths) == 0:
        raise Exception(f"No .ibsolution files found in {solution_path}")
    latest_version = "0.0.0"
    latest_path = ""
    for path in paths:
        p = pathlib.Path(path)
        sol_name = p.stem
        if solution_name and solution_name not in sol_name:
            continue
        version = sol_name.split("-")[-1]
        if version_tuple(version) > version_tuple(latest_version):
            latest_version = version
            latest_path = path
    return latest_path


def read_target_package():
    # Unzip solution into a temporary folder
    new_path = os.path.join(*TARGET_IB_PATH.split("/")[:-1], "temp_solution")
    path_to_ib_solution = get_latest_ibsolution_path(
        TARGET_IB_API_TOKEN, TARGET_IB_HOST, TARGET_IB_PATH
    )
    unzip_files(
        TARGET_IB_HOST, TARGET_IB_API_TOKEN, path_to_ib_solution, new_path
    )  # TODO: Does this unzip work on a non-zip file path like ib_solution_path?

    # Add wait for files to unzip
    time.sleep(5)

    # Read package
    package_json_path = os.path.join(new_path, "package.json")
    read_response = read_file_content_from_ib(
        TARGET_IB_HOST, TARGET_IB_API_TOKEN, package_json_path, use_clients=False
    )
    package_json = json.loads(read_response)

    # Delete temporary solution folder
    delete_folder_or_file_from_ib(
        new_path, TARGET_IB_HOST, TARGET_IB_API_TOKEN, use_clients=False
    )
    return package_json


def set_output_version_github(version):
    env_file = os.getenv("GITHUB_ENV")

    with open(env_file, "a") as myfile:
        myfile.write(f"PACKAGE_VERSION={version}")


def copy_solution_to_working_dir(new_solution_dir):
    package_path = os.path.join(SOURCE_SOLUTION_DIR, "package.json")
    icon_path = os.path.join(SOURCE_SOLUTION_DIR, "icon.png")
    flow_path = os.path.join(SOURCE_SOLUTION_DIR, REL_FLOW_PATH)
    modules_path = os.path.join(
        SOURCE_SOLUTION_DIR, *REL_FLOW_PATH.split("/")[:-1], "modules"
    )

    for path in [package_path, icon_path, flow_path, modules_path]:
        new_path = path.replace(SOURCE_SOLUTION_DIR, new_solution_dir)
        copy_file_within_ib(
            SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, path, new_path, use_clients=False
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--promote_solution_to_target", action="store_true")
    parser.add_argument("--publish_source_solution", action="store_true")
    parser.add_argument("--publish_target_solution", action="store_true")
    parser.add_argument("--upload_dependencies", action="store_true")
    parser.add_argument("--compile_source_solution", action="store_true")
    parser.add_argument("--set_github_actions_env_var", action="store_true")
    parser.add_argument("--set_azure_devops_env_var", action="store_true")
    parser.add_argument("--download_ibsolution", action="store_true")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--remote", dest="local", action="store_false")
    parser.add_argument("--local_flow", action="store_true")
    parser.add_argument("--remote_flow", action="store_true")
    parser.add_argument("--marketplace", action="store_true")
    parser.set_defaults(local=False)
    args = parser.parse_args()

    if args.compile_source_solution:
        new_solution_dir = os.path.join(
            SOURCE_WORKING_DIR, SOURCE_SOLUTION_DIR.split("/")[-1]
        )
        copy_solution_to_working_dir(new_solution_dir)
        time.sleep(3)
        compile_and_package_ib_solution(
            SOURCE_IB_HOST,
            SOURCE_IB_API_TOKEN,
            new_solution_dir,
            REL_FLOW_PATH,
            SOURCE_COMPILED_SOLUTIONS_PATH,
        )

    if args.publish_source_solution or args.local_flow or args.remote_flow:
        source_path = get_latest_ibsolution_path(
            SOURCE_IB_API_TOKEN, SOURCE_IB_HOST, SOURCE_COMPILED_SOLUTIONS_PATH
        )
        if args.marketplace:
            publish_to_marketplace(SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, source_path)
        else:
            deploy_solution(SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, source_path)

    if args.promote_solution_to_target or args.local_flow or args.remote_flow:
        if args.local or args.local_flow:
            upload_zip_to_instabase()

            # Unzip solution contents
            zip_path = os.path.join(*[TARGET_IB_PATH, LOCAL_SOLUTION_DIR + ".zip"])
            unzip_files(TARGET_IB_HOST, TARGET_IB_API_TOKEN, zip_path)

            directory_path = os.path.join(TARGET_IB_PATH, LOCAL_SOLUTION_DIR)
            time.sleep(3)
            compile_and_package_ib_solution(
                TARGET_IB_HOST,
                TARGET_IB_API_TOKEN,
                directory_path,
                REL_FLOW_PATH,
                TARGET_IB_PATH,
            )
        else:
            ib_solution_path = get_latest_ibsolution_path(
                SOURCE_IB_API_TOKEN, SOURCE_IB_HOST, SOURCE_COMPILED_SOLUTIONS_PATH
            )
            resp = download_ibsolution(
                SOURCE_IB_HOST, SOURCE_IB_API_TOKEN, ib_solution_path
            )
            target_path = os.path.join(TARGET_IB_PATH, ib_solution_path.split("/")[-1])
            upload_file(TARGET_IB_HOST, TARGET_IB_API_TOKEN, target_path, resp.content)

    if args.publish_target_solution or args.local_flow or args.remote_flow:
        ib_solution_path = get_latest_ibsolution_path(
            TARGET_IB_API_TOKEN, TARGET_IB_HOST, TARGET_IB_PATH
        )
        if args.marketplace:
            publish_to_marketplace(
                TARGET_IB_HOST, TARGET_IB_API_TOKEN, ib_solution_path
            )
        else:
            deploy_solution(TARGET_IB_HOST, TARGET_IB_API_TOKEN, ib_solution_path)

    if args.upload_dependencies or args.local_flow or args.remote_flow:
        if args.local:
            dependencies = read_local_package_json(LOCAL_SOLUTION_DIR)
            requirements_dict = parse_dependencies(dependencies.get("dependencies", {}))
        else:
            package = read_target_package()
            requirements_dict = parse_dependencies(package.get("dependencies", {}))

        # Download dependencies needed for ibsolution and upload them onto target environment
        uploaded_ibsolutions = download_dependencies_from_dev_and_upload_to_prod(
            SOURCE_IB_HOST,
            TARGET_IB_HOST,
            SOURCE_IB_API_TOKEN,
            TARGET_IB_API_TOKEN,
            SOURCE_WORKING_DIR,
            TARGET_IB_PATH,
            requirements_dict,
        )
        publish_dependencies(uploaded_ibsolutions, TARGET_IB_HOST, TARGET_IB_API_TOKEN)

    if args.download_ibsolution or args.local_flow or args.remote_flow:
        ib_solution_path = get_latest_ibsolution_path(
            TARGET_IB_API_TOKEN, TARGET_IB_HOST, TARGET_IB_PATH
        )
        download_ibsolution(
            TARGET_IB_HOST,
            TARGET_IB_API_TOKEN,
            ib_solution_path,
            write_to_local=True,
            unzip_solution=True,
        )

    if args.set_github_actions_env_var:
        if args.local:
            package = read_local_package_json(LOCAL_SOLUTION_DIR)
        else:
            package = read_target_package()
        version = package["version"]
        set_output_version_github(version)

    if args.set_azure_devops_env_var:
        if args.local:
            package = read_local_package_json(LOCAL_SOLUTION_DIR)
        else:
            package = read_target_package()
        version = package["version"]
        print(f"##vso[task.setvariable variable=PACKAGE_VERSION;]{version}")


if __name__ == "__main__":
    main()
