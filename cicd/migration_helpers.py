import logging
import json
import os
import time

import requests
from zipfile import ZipFile
from pathlib import Path

from cicd.ib_helpers import upload_chunks, read_file_through_api, package_solution, unzip_files, compile_solution, \
  copy_file_within_ib, read_file_content_from_ib, get_file_metadata, create_folder_if_it_does_not_exists, \
  wait_until_job_finishes


def parse_dependencies(package_dependencies):
  """
  Parses dependencies stored in a package.json file into a dictionary mapping model/dev package name to its
  version number

  :param package_dependencies: (dict) dictionary containing model + dev package dependencies. Assumes following format:
        {
          "models": [
            "model_Paystubs_9f7c5403ee91443cbd4c697281775683==0.0.5",
            "ib_handwriting==0.0.1"
          ],
          "dev_exchange_packages": [
            "ib_intelligence==0.0.8",
            "ib_signature==0.0.2",
            "ib_signature==0.0.2",
            "ibtools==1.0.6",
            "ib_validations==0.0.4",
            "model_util==1.1.3"
          ]
        }
  :return: dictionary mapping model/dev package name to a version number
  """
  models = {m.split('==')[0].strip(): m.split('==')[1].strip() for m in package_dependencies['models']}
  packages = {p.split('==')[0].strip(): p.split('==')[1].strip() for p in
              package_dependencies['dev_exchange_packages']}
  return {**packages, **models}


def get_dependencies_from_solution_build_folder(ib_host, api_token, solution_build_path):
  """
  Gets a solution's dependencies from its build folder. Assumes package.json exists in build folder

  :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
  :param solution_build_path: (string) path to solution build directory
  :param api_token: (string) api token for IB environment
  :return: dictionary from parse_dependencies
  """
  # Read package.json from solution build directory
  package_json_path = os.path.join(*[solution_build_path, 'package.json'])
  read_response = read_file_through_api(ib_host, api_token, package_json_path)
  package = json.loads(read_response.content)

  # Return dependencies from pacakge.json contents
  if 'dependencies' in package:
    return parse_dependencies(package['dependencies'])
  else:
    return {}


def get_dependencies_from_ibsolution(ib_host, api_token, solution_path):
  """
  Converts an .ibsolution file into a zip file and then unzips it to read its package.json and parse out its
  model + dev package dependencies

  :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
  :param api_token: (string) api token for IB environment
  :param solution_path: (string) path to .ibsolution file
  :return: dictionary from parse_dependencies
  """
  new_path = solution_path.replace('.ibsolution', '.zip')
  copy_file_within_ib(ib_host, api_token, solution_path, new_path)

  unzip_files(ib_host, api_token, new_path)

  return get_dependencies_from_solution_build_folder(ib_host, api_token, new_path.replace('.zip', ''))


def compile_and_package_ib_solution(ib_host, api_token, solution_directory_path, relative_flow_path, compiled_solution_output_folder_path):
    """
    Compiles a flow and packages resulting binary into a .ibsolution file

    :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
    :param api_token: (string) api token for IB environment
    :param solution_directory_path: (string) path to root folder of solution
                                    (e.g. ganan.prabaharan/testing/fs/Instabase Drive/testing_solution)
    :param relative_flow_path: (string) relative path of flow from solution_path (e.g. testing_flow.ibflow)
                               full flow path is {solutionPath}/{relative_flow_path}
    :param compiled_solution_output_folder_path: (string) path to place compiled ibsolution in
    :return: (Response object, Response object) responses for compile and package requests
    """
    compile_resp = compile_solution(ib_host, api_token, solution_directory_path, relative_flow_path)

    # Sleep to allow time for compilation
    time.sleep(6)

    solution_resp = package_solution(ib_host, api_token, solution_directory_path, compiled_solution_output_folder_path)
    return compile_resp, solution_resp


def download_ibsolution(ib_host, api_token, solution_path, write_to_local=False, unzip_solution=False):
  """
  Get the bytes content of an .ibsolution file

  :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
  :param api_token: (string) api token for IB environment
  :param solution_path: (str) path to ibsolution
  :param write_to_local: (bool) flag indicating whether to write .ibsolution bytes to local system
  :return: Response object
  """

  # TODO: Check if file exists first
  resp = read_file_through_api(ib_host, api_token, solution_path)

  if write_to_local:
    solution_name = Path(solution_path).name
    with open(solution_name, 'wb') as fd:
      fd.write(resp.content)

    if unzip_solution:
      zip_path = Path(solution_path).with_suffix(".zip").name
      with open(zip_path, 'wb') as fd:
        fd.write(resp.content)
      with ZipFile(zip_path, "r") as zip_ref:
        unzip_dir = Path(Path(zip_path).parent, Path(zip_path).stem)
        zip_ref.extractall(unzip_dir)
      os.remove(zip_path)

  return resp


def __copy_package_from_marketplace(ib_host, api_token, package_name, package_version, intermediate_path):
  """
  Uses marketplace copy API to copy an ibsolution to an intermediate location, and then downloads it

  :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
  :param api_token: (string) api token for IB environment
  :param package_name: (string) name of package (e.g. model_util)
  :param package_version: (string) version of package (e.g. 1.1.5)
  :param intermediate_path: (string) path to intermediate location to copy ibsolution to
                            (e.g. ganan.prabaharan/my-repo/fs/Instabase%20Drive/download_folder)
  :return:
  """
  solution_name = f'{package_name}-{package_version}.ibsolution'

  # TODO: Check if file exists
  # Get url to marketplace solution
  dev_marketplace_solution_url = os.path.join(
    ib_host, 'api/v1/drives/system/global/fs/Instabase%20Drive/Applications/Marketplace/All')
  dev_marketplace_solution_url = os.path.join(
    *[dev_marketplace_solution_url, package_name, package_version, solution_name])

  # Copy from marketplace to intermediate download location

  # add solution name to intermediate path if needed
  if not intermediate_path.endswith(solution_name):
    intermediate_path = os.path.join(intermediate_path, solution_name)

  # Send request to copy file from marketplace
  copy_url = os.path.join(dev_marketplace_solution_url, 'copy?is_v2=true')
  headers = {'Authorization': 'Bearer {0}'.format(api_token)}
  params = {'new_full_path': intermediate_path}
  resp = requests.post(copy_url, headers=headers, json=params, verify=False)

  # Copy task is async so wait for job to finish before continuing
  content = json.loads(resp.content)
  job_id = content['job_id']
  wait_until_job_finishes(ib_host, job_id, 'job', api_token)

  return intermediate_path


def check_if_file_exists_on_ib_env(ib_host, api_token, file_path, use_clients=False, **kwargs):
  """
  Determines if a file exists on IB environment
  Uses clients if user sets use_clients, otherwise uses Metadata API and checks if content length is greater than 100000

  :param ib_host: (string) IB host url (e.g. https://www.instabase.com)
  :param api_token: (string) api token for IB environment
  :param file_path: (string) path to file on IB environment
                    (e.g. ganan.prabaharan/my-repo/fs/Instabase%20Drive/package.json)
  :param use_clients:
  :param kwargs:
  :return:
  """

  if use_clients:
    # Use clients from kwargs if user sets flag to True
    clients, err = kwargs['_FN_CONTEXT_KEY'].get_by_col_name('CLIENTS')
    return clients.ibfile.is_file(file_path)
  else:
    # Check file metadata and determine if file already exists
    metadata_response = get_file_metadata(ib_host, api_token, file_path)
    if metadata_response.status_code == 200:
      try:
        content_length = metadata_response.headers['Content-Length']
        content_length = int(content_length)
        if content_length > 100000:
          # File exists
          return True
      except:
        pass

  return False


def copy_marketplace_package_and_move_to_new_env(source_ib_host, target_ib_host, package_name, package_version,
                                                 source_api_token, target_api_token, download_folder, prod_upload_folder,
                                                 use_clients=False, **kwargs):
  """
  Function to download ibsolutions from dev marketplace to prod ma

  :param source_ib_host: (string) IB host url for env where package exists (e.g. https://www.instabase.com)
  :param target_ib_host: (string) IB host url for env to move package to (e.g. https://www.instabase.com)
  :param package_name: (string) name of package (e.g. model_util)
  :param package_version: (string) version of package (e.g. 1.1.5)
  :param source_api_token: (string) api token for source env
  :param target_api_token: (string) api token for target env
  :param download_folder: (string) intermediate folder on source env to copy package to
  :param prod_upload_folder: (string) folder on taregt env to copy package to
  :param use_clients: (bool) flag indicating whether to use clients from a flow
  :param kwargs: kwargs from flow
  :return: Tuple(Response object, string) - Tuple of upload chunks response, and string of path to uploaded file
  """
  # Create final upload path
  solution_name = f'{package_name}-{package_version}.ibsolution'
  final_upload_path = os.path.join(prod_upload_folder, solution_name)

  # Check file metadata and determine if file already exists
  metadata_response = get_file_metadata(target_ib_host, target_api_token, final_upload_path)
  if metadata_response.status_code == 200:
    try:
      content_length = metadata_response.headers['Content-Length']
      content_length = int(content_length)
      if content_length > 100000:
        # File exists
        return None, final_upload_path
    except:
      pass

  # If file doesn't exist in target env, copy it to a temporary download folder on source env
  # and then move it to target env
  copy_to_path = os.path.join(download_folder, solution_name)

  # Check if file exists in temp download folder on source env, if it doesn't exist then copy it over
  if not check_if_file_exists_on_ib_env(source_ib_host, source_api_token, copy_to_path, use_clients, **kwargs):
    __copy_package_from_marketplace(source_ib_host, source_api_token, package_name, package_version, copy_to_path)

  # Download file contents of ibsolution from source env download folder
  file_contents = read_file_content_from_ib(source_ib_host, source_api_token, copy_to_path, use_clients, **kwargs)

  # Upload file contents to target env upload folder
  resp = upload_chunks(target_ib_host, final_upload_path, target_api_token, file_contents)
  return resp, final_upload_path


def download_dependencies_from_dev_and_upload_to_prod(source_ib_host, target_ib_host, source_api_token,
                                                      target_api_token, download_folder_path, upload_folder_path,
                                                      dependency_dict, use_clients=False, **kwargs):
  """
  Downloads dependencies listed in dependency_dict to a folder called 'dev_dependencies' on dev environment,
  and uploads them to a folder called 'prod_dependencies' on prod environment

  :param source_ib_host: (string) IB host url for env where package exists (e.g. https://www.instabase.com)
  :param target_ib_host: (string) IB host url for env where package exists (e.g. https://www.instabase.com)
  :param source_api_token: (string) api token for source_ib_host env
  :param target_api_token: (string) api token for target_ib_host env
  :param download_folder_path: (string) path to folder on source_ib_host env to create download folder in
                                        (used to copy marketplace packages to)
                               (e.g. ganan.prabaharan/my-repo/fs/Instabase%20Drive/)
  :param upload_folder_path: (string) path to folder on target_ib_host env to create upload folder in
                                        (used to upload marketplace packages to)
                               (e.g. ganan.prabaharan/my-repo/fs/Instabase%20Drive/)
  :param dependency_dict: (dict) Dictionary mapping package names to their version numbers
  :param use_clients: (bool) flag indicating whether to use clients from a flow
  :param kwargs: kwargs from flow
  :return: List[str] list of paths for uploaded solutions
  """
  # TODO: Give possibility to use clients for one environment and the other

  # Create download/upload folders on dev/prod environments
  source_download_folder = os.path.join(download_folder_path, 'source_dependencies')
  target_upload_folder = os.path.join(upload_folder_path, 'target_dependencies')

  create_folder_if_it_does_not_exists(source_ib_host, source_api_token, source_download_folder)
  create_folder_if_it_does_not_exists(target_ib_host, target_api_token, target_upload_folder)

  # Copy all dependency packages from dev to prod
  upload_paths = []
  for package_name, package_version in dependency_dict.items():
    try:
      resp, uploaded_path = copy_marketplace_package_and_move_to_new_env(source_ib_host, target_ib_host,
                                                                         package_name,
                                                                         package_version, source_api_token,
                                                                         target_api_token, source_download_folder,
                                                                         target_upload_folder,
                                                                         use_clients=use_clients,
                                                                         **kwargs)
    except Exception as e:
      logging.error(
        'Error moving package name: {}, package_version: {}. Error: {}'.format(package_name, package_version, e))
      continue

    # Keep track pf uploaded paths
    upload_paths.append(uploaded_path)

  return upload_paths
