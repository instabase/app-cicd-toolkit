## Overview

CI/CD solution to migrate a local solution to a target instabase environment.

The solution uses Instabase APIs and CI tooling to promote solutions between environments. Template CI pipelines for GitHub Actions and Azure DevOps are provided and should be updated to suit customer's needs.

### Python Scripts

#### Filesystem projects: promote_solution.py

The Python `promote_solution.py` script calls Instabase APIs and can execute the following steps when the corresponding flags are passed in:

- `--compile_source_solution`
  - Compiles solution in source environment in path specified in `SOURCE_SOLUTION_DIR` environment variable.
- `--publish_source_solution`
  - Publishes the latest version of the solution in the source environment to Deployed Solutions
- `--promote_solution_to_target`
  - Uploads to the solution to the target environment
- `--publish_target_solution`
  - Publishes the latest version of the solution in the target environment to Deployed Solutions. Use the `--local` flag to upload code in the git repository
- `--upload_dependencies`
  - Uploads and publishes the solution dependencies to the target environment based on dependencies listed in `package.json`
- `--download_ibsolution`
  - Downloads the `.ibsolution` file to the local filesystem
- `--set_github_actions_env_var`
  - Sets `PACKAGE_VERSION` environment variable to be used in later steps in the GitHub Actions pipleline
- `--set_azure_devops_env_var`
  - Sets `PACKAGE_VERSION` environment to be used in later steps in the Azure DevOps pipeline
- `--local`
  - To be used alongside above flags. This will promote a solution from the codebase rather than a remote Instabase environment
- `--remote`
  - To be used alongside above flags. This will promote a solution from a source Instbase environment
- `--local_flow`
  - Performs series of above steps for a local workflow
- `--remote_flow`
  - Performs series of above steps for a remote workflow, `--compile_source_solution`, `--set_azure_devops_env_var`, and `--set_github_actions_env_var` are not included in these so need to be used too
- `--marketplace`
  - Publishes solution to Marketplace. If not used then Deployed Solutions will be used

#### Solution builder projects: promote_sb_solution.py

- `--compile_source_solution`
  - Compiles solution in source environment in path specified in `SOURCE_SOLUTION_DIR` environment variable.
- `--deploy_source_solution`
  - Publishes the latest version of the solution in the source environment to Deployed Solutions
- `--promote_solution_to_target`
  - Uploads to the solution to the target environment
- `--deploy_target_solution`
  - Publishes the latest version of the solution in the target environment to Deployed Solutions
- `--upload_dependencies`
  - Uploads and publishes the solution dependencies to the target environment based on dependencies listed in `package.json`
- `--download_ibsolution`
  - Downloads the `.ibsolution` file to the local filesystem
- `--set_github_actions_env_var`
  - Sets `PACKAGE_VERSION` environment variable to be used in later steps in the GitHub Actions pipleline
- `--set_azure_devops_env_var`
  - Sets `PACKAGE_VERSION` environment to be used in later steps in the Azure DevOps pipeline
- `--remote_flow`
  - Performs series of above steps for a remote workflow, `--compile_source_solution`, `--set_azure_devops_env_var`, `--download_ibsolution`, and `--set_github_actions_env_var` are not included in these so need to be used too

### GitHub Actions Workflows

The `local-github-actions` automated pipeline runs on successful merge to main, so the main branch of the project should mirror the target environment. The `remote-github-actions-workflow` is manually run.

The pipeline sets environment variables from GitHub secrets and variables and runs the Python script. It then creates a release stores the downloaded `.ibsolution` file as an artifact.

## Setup

### Running locally

If you're not using CI tooling and running the script locally you will need to set the below environment variables. There is an option to store these variables in a `.env` file which will get loaded in using `load_dotenv()` at the beginning of the script

### Configure Repo

#### Filesystem project configuration

1. Set the following git secrets in Settings > Secrets and Variables > Actions:
    - **SOURCE_IB_API_TOKEN** API token for source environment. Ideally both tokens should belong to a service account
    - **TARGET_IB_API_TOKEN** API token for target environment
2. Set git variables in the same place:
    - **SOURCE_IB_HOST** e.g. "https://solution-eng.aws.sandbox.instabase.com"
    - **SOURCE_WORKING_DIR** Path in source IB environment's filesystem to use for downloading dependencies
    - **SOURCE_SOLUTION_DIR** Path to the solution directory in the source Instabase environment
    - **LOCAL_SOLUTION_DIR** Directory in local repository that contains IB solution code, if using a remote flow leave a blank string
    - **REL_FLOW_PATH** Path to flow relative to Instabase solution e.g. in "path/to/solution/Flow/some_flow.ibflow" where "path/to/solution" is `SOURCE_SOLUTION_DIR` it would be "Flow/some_flow.ibflow"
    - **SOURCE_COMPILED_SOLUTIONS_PATH** Path to where `.ibsolution` files are generated. This will usually be one level higher than the `SOURCE_SOLUTION_DIR`
    - **TARGET_IB_HOST** e.g. "https://instabase.com"
    - **TARGET_IB_PATH** Path in the target IB environment where the solution will get uploaded
3. Copy `cicd` folder into repository and move one of the `.yml` template workflow files into a `.GitHub/workflows` folder

#### Solution builder project configuration

1. Set the following git secrets in Settings > Secrets and Variables > Actions:
    - **SOURCE_IB_API_TOKEN** API token for source environment. Ideally both tokens should belong to a service account
    - **TARGET_IB_API_TOKEN** API token for target environment
2. Set git variables in the same place:
    - **SOURCE_IB_HOST** e.g. "https://solution-eng.aws.sandbox.instabase.com"
    - **SOURCE_WORKING_DIR** Path in source IB environment's filesystem to use for downloading dependencies and storing ibsolution files
    - **TARGET_IB_HOST** e.g. "https://instabase.com"
    - **TARGET_IB_PATH** Path in the target IB environment where the solution will get uploaded
    - **SOLUTION_BUILDER_NAME** Name of solution builder project
    - **FLOW_NAME** Name of flow to promote
    - **WORKSPACE_DRIVE_PATH** Path in source IB environment's filesystem to the drive where the solution builder project is stored, e.g. hannahroiter/ci-cd/fs/Instabase Drive
    - **DEPENDENCIES** String representation of list of model and marketplace package dependencies in the format `model_name==0.0.1,package_name==0.4.5,second_package==0.0.1`
3. Copy `cicd` folder into repository and move one of the `.yml` template workflow files into a `.GitHub/workflows` folder

### Local Workflow - filesystem projects only

1. Develop in IB environment.
2. Once happy with changes checkout a new git branch and copy the solution directory into codebase.
3. Make sure this includes a `package.json` file and an `icon.png` at the top level of the solution code, bump the version in `package.json`
4. Include any dependencies in the `package.json` file in the format: ```"dependencies": {
    "models": ["model_for_cicd==0.0.1"],
    "dev_exchange_packages": ["package_for_cicd==0.0.1"]
  }```
5. If using Deployed solutions, ensure the `package.json` file includes `owner` and `visibility` fields
6. Any final changes e.g. linting
7. Push local branch to git
8. Pull request to main
9. On merge the GitHub actions workflow will:
   1. Run the Python script with `--local_flow` parameters (see above for steps)
   2. Create a GitHub release with tag equal to the version stored in `package.json`
   3. Upload the `.ibsolution` file to the release artifacts

### Remote Workflow

#### Filesystem projects

1. Develop in IB environment.
2. If in a development environment, bump up the version in `package.json` and ensure that `package.json` and `icon.png` files are in the top level of the directory
3. If using Deployed solutions, ensure the `package.json` file includes fields `owner` set to `IB_DEPLOYED` and `visibility` set to `PUBLIC`
4. Manually run the GitHub actions workflow which will:
   1. Run the Python script with `--remote_flow` parameters (see above for steps). If needed also pass in the `--compile_solution` parameter (likely to be needed in a DEV -> UAT workflow but not in UAT -> PROD)
   2. Commit and push the `.ibsolution` file to the repository
   3. Create a GitHub release with tag equal to the version stored in `package.json`
   4. Upload the `.ibsolution` file to the release artifacts
5. This will compile the solution in the source environment, promote it to the target environment, and store the `.ibsolution` file in the GitHub release

#### Solution builder projectts

1. Develop in IB environment.
2. Manually run the Github actions workflow which will:
   1. Run the `promote_sb_solution.py` python script with `--remote_flow` parameters, include `--compile_source_solution` parameter if moving a solution builder project from DEV -> UAT.
   2. Commit and push the `.ibsolution` file to the repository
   3. Create a GitHub release with tag equal to the version of the promoted solution
   4. Upload the `.ibsolution` file to the release artifacts
3. This will compile the solution in the source environment, promote it to the target environment, and store the `.ibsolution` file in the GitHub release

### Sample package.json (filesystem projects only)

```{
  "name": "Form W-2",
  "version": "0.0.2",
  "short_description": "Automatically process Form W-2",
  "long_description": "Extract key fields from Tax Form W-2 in the United States",
  "authors": [
    "Instabase"
  ],
  "solution_type": "ibflowbin",
  "accelerator_type": [
    "solution"
  ],
  "industry": [
    "Financial Services"
  ],
  "business_vertical": [
    "Retail & Consumer Banking"
  ],
  "use_case": [
    "Account Opening"
  ],
  "icon_file": "icon.png",
  "beta": true,
  "encryption_config": {
    "encryption_type": "v1"
  },
  "dependencies": {
    "models": ["model_for_cicd==0.0.1"],
    "dev_exchange_packages": ["package_for_cicd==0.0.1"]
  },
  "owner": "IB_DEPLOYED",
  "visibility": "PUBLIC"
}```