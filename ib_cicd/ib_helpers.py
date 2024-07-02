import os
from io import BytesIO
import requests
import json
from urllib.parse import quote
import time
import logging
import pathlib


def __get_file_api_root(ib_host, api_version="v2", add_files_suffix=True):
    """
    Gets file api root from an ib host url
    E.g.
    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_version: (string) api_version to add to ib_host to create file api root url
    :param add_files_suffix: (bool) flag indicating whether to add 'files' suffix to the api root
    :return: (string) IB host + file api root (e.g. https://www.instabase.com/api/v2/files)
    """

    # Add 'files' suffix if required
    if add_files_suffix:
        return os.path.join(*[ib_host, "api", api_version, "files"])

    return os.path.join(*[ib_host, "api", api_version])


def upload_chunks(ib_host, path, api_token, file_data):
    """
    Uploads bytes to a location on the Instabase environment
    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param path: (string) path on IB environment to upload to
    :param api_token: (string) API token for IB environment
    :param file_data: (bytes) Data to upload (bytes)
    :return: Response object
    """
    part_size = 10485760

    file_api_root = __get_file_api_root(ib_host)
    append_root_url = os.path.join(file_api_root, path)

    headers = {
        "Authorization": "Bearer {0}".format(api_token),
    }

    # Send data in parts
    bytes_io_content = BytesIO(file_data)
    with bytes_io_content as f:
        # Create parts from bytes data
        part_num = 0
        for chunk in iter(lambda: f.read(part_size), b""):
            if part_num == 0:
                headers["IB-Cursor"] = "0"
            else:
                headers["IB-Cursor"] = "-1"

            # Send patch request for part upload
            resp = requests.patch(
                append_root_url, headers=headers, data=chunk, verify=False
            )
            part_num += 1

    if resp.status_code != 204:
        raise Exception(f"Upload failed: {resp.content}")
    return resp


def upload_file(ib_host, api_token, file_path, file_data):
    """
    Upload single file to path on IB environment

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) API token for IB environment
    :param file_path: (string) path on IB environment to upload to
    :param file_data: (bytes) Data to upload (bytes)
    :return: Response object
    """
    file_api_root = __get_file_api_root(ib_host)
    url = os.path.join(file_api_root, file_path)
    headers = {"Authorization": "Bearer {0}".format(api_token)}

    resp = requests.put(url, headers=headers, data=file_data, verify=False)
    logging.info(f"File upload status : {resp.status_code}")

    if resp.status_code != 204:
        raise Exception(f"Upload file failed: {resp.content}")

    return resp


def read_file_through_api(ib_host, api_token, path_to_file):
    """
    Read file from IB environment
    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param path_to_file: (string) path to file on IB environment
                         (e.g. ganan.prabaharan/testing/fs/Instabase Drive/testing_flow)
    :param api_token: (string) API token for IB environment
    :return: Response object
    """
    file_api_root = __get_file_api_root(ib_host)
    url = os.path.join(*[file_api_root, path_to_file])

    params = {"expect-node-type": "file"}
    headers = {
        "Authorization": "Bearer {0}".format(api_token),
    }
    resp = requests.get(url, headers=headers, params=params, verify=False)

    if resp.status_code != 200:
        raise Exception(f"Error reading file: {resp.content}, for url: {url}")

    return resp


def publish_to_marketplace(ib_host, api_token, ibsolution_path):
    """
    Publishes an ibsolution to Marketplace

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) API token for IB environment
    :param ibsolution_path: path to .ibsolution file
    :return: Response object
    """
    file_api_v1 = __get_file_api_root(ib_host, api_version="v1", add_files_suffix=False)
    headers = {"Authorization": "Bearer {0}".format(api_token)}
    url = f"{file_api_v1}/marketplace/publish"

    args = {
        "ibsolution_path": ibsolution_path,
    }
    json_data = json.dumps(args)

    resp = requests.post(url, headers=headers, data=json_data, verify=False)
    try:
        resp = resp.json()
        logging.info(f"File: {url}, Solution publish status: {resp}")
    except:
        logging.info(
            f"Error publishing ibsolution_path: {ibsolution_path}. Solution publish status exception: {resp.content}"
        )

    return resp


def package_solution(ib_host, api_token, content_folder, output_folder):
    """
    Publish a directory as a solution

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param content_folder: (string) path to solution build directory
    :param output_folder: (string) path to create .ibsolution in
    :return: Response object
    """
    # Url for packaging solution build directory into an .ibsolution file
    create_solution_url = os.path.join(*[ib_host, "api/v1", "solution", "create"])
    headers = {"Authorization": "Bearer {0}".format(api_token)}

    args = {"content_folder": content_folder, "output_folder": output_folder}
    json_data = json.dumps(args)

    resp = requests.post(
        create_solution_url, headers=headers, data=json_data, verify=False
    )

    # Verify request was completed successful
    content = json.loads(resp.content)
    if resp.status_code != 200 or (
        "status" in content and content["status"] == "ERROR"
    ):
        raise Exception(f"Error with compile solution job: {resp.content}")

    return resp


def unzip_files(ib_host, api_token, zip_path, destination_path=None):
    """
    Unzip file on IB environment

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param zip_path: (string) path to zip file on IB environment
    :param destination_path: (string) path to unzip files to
    :return: Response object
    """
    # Unzip files url
    url = os.path.join(*[ib_host, "api/v2", "files", "extract"])
    destination_path = (
        destination_path if destination_path else ".".join(zip_path.split(".")[:-1])
    )
    headers = {"Authorization": "Bearer {0}".format(api_token)}

    data = json.dumps({"src_path": zip_path, "dst_path": destination_path})

    resp = requests.post(url, headers=headers, data=data, verify=False)

    if resp.status_code != 202:
        raise Exception(f"Unable to unzip files: {resp.content}")

    return resp


def compile_solution(
    ib_host,
    api_token,
    solution_path,
    relative_flow_path=None,
    solution_builder=False,
    solution_version=None,
):
    """
    Compiles a flow

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param solution_path: (string) path to root folder of solution
                              (e.g. ganan.prabaharan/testing/fs/Instabase Drive/testing_solution)
    :param relative_flow_path: relative path of flow from solution_path (e.g. testing_flow.ibflow)
                               full flow path is {solutionPath}/{relative_flow_path} (used for filesystem projects only)
    :param solution_builder: (bool) if the solution to be compiled is a solution builder project
    :param solution_version: (string) version of compiled solution (used for solution builder projects only)
    :return: Response object
    """
    # TODO: API docs issue
    path_encoded = quote(solution_path)

    url = os.path.join(*[ib_host, "api/v1", "flow_binary", "compile", path_encoded])

    if solution_builder:
        p = pathlib.Path(solution_path)
        bin_path = os.path.join(
            *p.parts[:-1], "builds", f"{solution_version}.ibflowbin"
        )
        flow_project_root = os.path.join(*p.parts[:7])
        flow_path = os.path.join(*p.parts[7:])
    else:
        bin_path = relative_flow_path.replace(".ibflow", ".ibflowbin")
        bin_path = os.path.join(solution_path, bin_path)
        flow_project_root = os.path.join(
            solution_path, *relative_flow_path.split("/")[:-1]
        )
        flow_path = relative_flow_path.split("/")[-1]

    headers = {"Authorization": "Bearer {0}".format(api_token)}
    data = json.dumps(
        {
            "binary_type": "Single Flow",
            "flow_project_root": flow_project_root,
            "predefined_binary_path": bin_path,
            "settings": {
                "flow_file": flow_path,
                "is_flow_v3": True,
            },
        }
    )
    resp = requests.post(
        url.replace("//d", "/d"), headers=headers, data=data, verify=False
    )

    # Verify request is successful
    content = json.loads(resp.content)
    if resp.status_code != 200 or (
        "status" in content and content["status"] == "ERROR"
    ):
        raise Exception(f"Error with compile solution job: {resp.content}")

    return resp


def copy_file_within_ib(
    ib_host, api_token, source_path, destination_path, use_clients=False, **kwargs
):
    """
    Copies a file within an IB environment

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param source_path: (string) path of file to copy
    :param destination_path: (string) path to copy to
    :param api_token: (string) api token for IB environment
    :param use_clients: (bool) flag indicating whether to use clients (if calling within flow) or file read API
    :return: Response object if use_clients is False
    """

    if use_clients:
        clients, err = kwargs["_FN_CONTEXT_KEY"].get_by_col_name("CLIENTS")
        copy, err = clients.ibfile.copy(source_path, destination_path)
        if err:
            logging.error(f"Error copying file: {err}")
    else:
        file_api_root = __get_file_api_root(ib_host)
        url = os.path.join(file_api_root, "copy")
        headers = {"Authorization": "Bearer {0}".format(api_token)}

        data = json.dumps({"src_path": source_path, "dst_path": destination_path})

        resp = requests.post(url, headers=headers, data=data, verify=False)

        if resp.status_code != 202:
            raise Exception(f"Error copying file: {resp.content}")

        return resp


def read_file_content_from_ib(
    ib_host, api_token, file_path_to_read, use_clients=False, **kwargs
):
    """
    Reads the content of a file on the IB environment.
    User can determine whether to use API or use clients (if calling within flow)

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param file_path_to_read: (string) path of file to read from IB environment
                              (e.g. ganan.prabaharan/testing/fs/Instabase Drive/test.txt)
    :param use_clients: (bool) flag indicating whether to use clients (if calling within flow) or file read API
    :param kwargs: kwargs from flow
    :return: (bytes) file content
    """

    if not use_clients:
        # Use file read API if use_clients flag is set to False
        resp = read_file_through_api(ib_host, api_token, file_path_to_read)
        return resp.content
    else:
        # Use clients if use_clients flag is set to True
        clients, err = kwargs["_FN_CONTEXT_KEY"].get_by_col_name("CLIENTS")

        # Check if file exists before attempting to read from it
        if clients.ibfile.is_file(file_path_to_read):
            file_content, err = clients.ibfile.read_file(file_path_to_read)
            if err:
                logging.info("is file read err: {}".format(err))
            return file_content
        else:
            logging.info("Not valid file: {}".format(file_path_to_read))


def get_file_metadata(ib_host, api_token, file_path):
    """
    Get metadata of file (using file API)

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param file_path: (string) path to file to read metadata from
                     (e.g. ganan.prabaharan/testing/fs/Instabase Drive/test.txt)
    :return: Response Object
    """
    file_api_root = __get_file_api_root(ib_host)
    url = os.path.join(file_api_root, file_path)

    headers = {
        "Authorization": "Bearer {0}".format(api_token),
        "IB-Retry-Config": json.dumps({"retries": 2, "backoff-seconds": 1}),
    }

    r = requests.head(url, headers=headers)
    return r


def create_folder_if_it_does_not_exists(ib_host, api_token, folder_path):
    """
    Creates a folder in an IB environment if it doesn't exist

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param folder_path: (string) path to folder on IB environment
    :param api_token: (string) api token for IB environment
    :return: Response object
    """
    file_api_root = __get_file_api_root(ib_host)
    metadata_url = os.path.join(file_api_root, folder_path)
    headers = {"Authorization": "Bearer {0}".format(api_token)}

    r = requests.head(metadata_url, headers=headers, verify=False)
    if r.status_code == 404:
        create_url = os.path.dirname(metadata_url)
        folder_name = os.path.basename(folder_path)
        data = json.dumps({"name": folder_name, "node_type": "folder"})
        resp = requests.post(create_url, headers=headers, data=data, verify=False)
        return resp


def check_job_status(ib_host, job_id, job_type, api_token):
    """
    Checks on status of a job id using the Job Status API (https://www.instabase.com/docs/apis/jobs/index.html#job-status)

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param job_id: (string) job id to look into
    :param job_type: (string) job type [flow, refiner, job, async, group]
    :param api_token: (string) api token for IB environment
    :return: Response object
    """
    url = ib_host + f"/api/v1/jobs/status?job_id={job_id}&type={job_type}"

    headers = {"Authorization": "Bearer {0}".format(api_token)}

    resp = requests.get(url, headers=headers, verify=False)

    # Verify request is successful
    content = json.loads(resp.content)
    if resp.status_code != 200 or (
        "status" in content and content["status"] == "ERROR"
    ):
        raise Exception(f"Error checking job status: {resp.content}")

    return resp


def list_directory(ib_host, folder, api_token):
    """
    Lists a directory on the IB filesystem and returns full paths

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param folder: (string) path to folder to list
    :param api_token: (string) api token for IB environment
    :return: (list) List of paths in directory
    """
    file_api_root = __get_file_api_root(ib_host)
    url = os.path.join(file_api_root, folder)

    headers = {"Authorization": "Bearer {0}".format(api_token)}

    paths = []
    has_more = None
    start_token = None

    while has_more is not False:
        params = {"expect-node-type": "folder", "start-token": start_token}
        resp = requests.get(url, headers=headers, params=params)

        # Verify request is successful
        content = json.loads(resp.content)
        if resp.status_code != 200 or (
            "status" in content and content["status"] == "ERROR"
        ):
            raise Exception(f"Error checking job status: {resp.content}")

        nodes = content["nodes"]
        paths += [node["full_path"] for node in nodes]

        has_more = content["has_more"]
        start_token = content["next_page_token"]
    return paths


def wait_until_job_finishes(ib_host, job_id, job_type, api_token):
    """
    Helper function to continuously wait until a job finishes (uses job status api to determine this)

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param job_id: (string) job id to look into
    :param job_type: (string) job type [flow, refiner, job, async, group]
    :param api_token: (string) api token for IB environment

    :return: bool indicating whether job completed successfully
    """
    still_running = True
    while still_running:
        job_status_response = check_job_status(ib_host, job_id, job_type, api_token)
        job_status_response_content = json.loads(job_status_response.content)
        status = job_status_response_content["status"]
        state = job_status_response_content["state"]

        if status != "OK":
            return False

        still_running = state != "DONE" and state != "COMPLETE"
        time.sleep(5)

    return True


def delete_folder_or_file_from_ib(
    path_to_delete, ib_host=None, api_token=None, use_clients=False, **kwargs
):
    """
    Delete a folder from Instabase
    :param path_to_delete: (string) path of file to read from IB environment
                           (e.g. ganan.prabaharan/testing/fs/Instabase Drive/test.txt)
    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param use_clients:
    :param kwargs:
    :return:
    """
    if use_clients:
        # Use clients if use_clients flag is set to True
        clients, err = kwargs["_FN_CONTEXT_KEY"].get_by_col_name("CLIENTS")
        rm, err = clients.ibfile.rm(path_to_delete)
    else:
        # Use Filesystem API to delete file/folder
        file_api_root = __get_file_api_root(ib_host)
        url = os.path.join(file_api_root, path_to_delete)

        headers = {"Authorization": "Bearer {0}".format(api_token)}

        # TODO: Check status code
        r = requests.delete(url, headers=headers, verify=False)


def deploy_solution(ib_host, api_token, ibsolution_path):
    """
    Deploys a solution
    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param ibsolution_path: (string) path to .ibsolution file to deploy
    :return: Response object return from deploy request
    """
    file_api_root = __get_file_api_root(ib_host, add_files_suffix=False)
    headers = {"Authorization": "Bearer {0}".format(api_token)}
    url = f"{file_api_root}/solutions/deployed"

    args = {
        "solution_path": ibsolution_path,
    }
    json_data = json.dumps(args)

    resp = requests.post(url, headers=headers, data=json_data, verify=False)

    try:
        job_id = json.loads(resp.content)["job_id"]
        logging.info(f"Solution deployed with job ID {job_id}")
    except:
        logging.warning(f"Solution publish status exception: {resp.content}")

    return resp
