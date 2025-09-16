# pattern-service

Hi there! We're excited to have you as a contributor.

## Table of contents

- [pattern-service](#pattern-service)
  - [Table of contents](#table-of-contents)
  - [Things to know prior to submitting code](#things-to-know-prior-to-submitting-code)
  - [Build and Run the Development Environment](#build-and-run-the-development-environment)
    - [Clone the repo](#clone-the-repo)
    - [Configure Python environment](#configure-python-environment)
    - [Set env variables for development](#set-env-variables-for-development)
    - [Configure postgres and run the dispatcher service](#configure-postgres-and-run-the-dispatcher-service)
    - [Configure and run the application](#configure-and-run-the-application)
    - [Development Configuration](#development-configuration)
  - [Updating dependencies](#updating-dependencies)
  - [Running linters and code checks](#running-linters-and-code-checks)
  - [Running tests](#running-tests)
  - [Building API Documentation](#building-api-documentation)

## Things to know prior to submitting code

- All code submissions are done through pull requests against the `main` branch.
- Take care to make sure no merge commits are in the submission, and use `git rebase` vs `git merge` for this reason.
- If collaborating with someone else on the same branch, consider using `--force-with-lease` instead of `--force`. This will prevent you from accidentally overwriting commits pushed by someone else. For more information, see [git push docs](https://git-scm.com/docs/git-push#git-push---force-with-leaseltrefnamegt).
- We ask all of our community members and contributors to adhere to the [Ansible code of conduct](http://docs.ansible.com/ansible/latest/community/code_of_conduct.html). If you have questions, or need assistance, please reach out to our community team at [codeofconduct@ansible.com](mailto:codeofconduct@ansible.com)

## Build and Run the Development Environment

### Clone the repo

If you have not already done so, you will need to clone, or create a local copy, of the [pattern-service repository](https://github.com/ansible/pattern-service).
For more on how to clone the repo, view [git clone help](https://git-scm.com/docs/git-clone).
Once you have a local copy, run the commands in the following sections from the root of the project tree.

### Configure Python environment

Ensure you are using a supported Python version, defined in the [pyproject.toml file](./pyproject.toml).

Create python virtual environment using one of the below commands:

`virtualenv --python 3.x /path/to/virtual_env` or `python3.x -m venv /path/to/virtual_env`

Set the virtual environment

`source /path/to/virtualenv/bin/activate/`

Install required python modules for development

`pip install -r requirements/requirements-dev.txt`

For standalone development tools written in Python, such as `pre-commit` and `pip-tools`, we recommend using your system package manager, `pipx` tool or `pip` user install mode (`pip install --user`), in decreasing order of preference.

### Set env variables for development

Either create a .env file in the project root containing the following env variables, or export them to your shell env:

```bash
PATTERN_SERVICE_MODE=development
```

### Configure postgres and run the dispatcher service

Several endpoints in the pattern service rely on asynchronous tasks that are handled by a separate running service, the dispatcher service. This uses [PostgreSQL's](https://www.postgresql.org/) `pg_notify` ability to send asyncronous tasks from the django application to the dispatcher service. For more details, see the [dispatcherd documentation](https://github.com/ansible/dispatcherd/blob/main/README.md).

To make use of the dispatcher, you will need to ensure that both postgres and the dispatcher service are running. _The easiest way to do this is via [docker-compose](./tools/podman/README.md)_, however it is also possible to do this manually as follows:

- Install postgres locally and create a database for the service.
- Update your local .env file to reference your postgres server and database details (these can also be exported to your shell env):

```bash
PATTERN_SERVICE_DB_NAME=<your database name>
PATTERN_SERVICE_DB_USER=<your database user>
PATTERN_SERVICE_DB_PASSWORD=<your database user password>
PATTERN_SERVICE_DB_HOST=localhost
PATTERN_SERVICE_DB_PORT="5432 (or your postgres port)"
```

- Run the dispatcherd service from the root pattern service directory with `python manage.py worker`

### Configure and run the application

In a separate terminal window, run:

`python manage.py migrate && python manage.py runserver`

The application can be reached in your browser at `https://localhost:8000/`. The Django admin UI is accessible at `https://localhost:8000/admin` and the available API endpoints will be listed in the 404 information at `http://localhost:8000/api/pattern-service/v1/`.

### Development Configuration

Default configuration values for connecting to the Ansible Automation Platform (AAP) service are defined in `development_defaults.py`:

```bash
AAP_URL = "http://localhost:44926"        # Base URL of your AAP instance
AAP_VALIDATE_CERTS = False                # Whether to verify SSL certificates
AAP_USERNAME = "admin"                    # Username for AAP authentication
AAP_PASSWORD = "password"                 # Password for AAP authentication
```

_Note_: These defaults are placeholders for local development only. You must provide proper values for your environment by setting environment variables prefixed with `PATTERN_SERVICE_` or via a `.env` file.
For example:

```bash
export PATTERN_SERVICE_AAP_URL="http://your-ip-address:44926"
export PATTERN_SERVICE_AAP_VALIDATE_CERTS="False"
export PATTERN_SERVICE_AAP_USERNAME="admin"
export PATTERN_SERVICE_AAP_PASSWORD="your-password"
```

This ensures secure and correct operation in your deployment or testing environment.

Dynaconf will prioritize environment variables and values in `.env` over defaults in `development_defaults.py`.

## Updating dependencies

Project dependencies for all environments are specified in the [pyproject.toml file](./pyproject.toml). A requirements.txt file is generated for each environment using pip-compile, to simplify dependency installation with pip.

To add a new dependency:

1. Ensure you have `pip-tools` installed by running either `pipx install pip-tools` or `pip install -u pip-tools`.
2. Add the package to the appropriate project or optional dependencies section of the pyproject.toml file, using dependency specifiers to constrain versions.
3. Update the requirements files with the command `make requirements`. This should update the relevant requirements.txt files in the project's requirements directory.

## Running linters and code checks

Linters, type checks, and other checks can all be run via `tox`. To see the available `tox` commands for this project, run `tox list`.

To run an individual tox command use the `-e` flag to specify the environment, for example: `tox -e lint` to run the linters.

To run all checks, simply run `tox` with no options.

## Running tests

Running the tests requires a postgres connection. The easiest way to do this is with the [test compose file](./tools/podman/compose-test.yaml), and there is a `make` command to simplify starting the postgres container and running the tests:

```bash
make test
```

## Building API Documentation

The pattern service includes support for generating an OpenAPI Description of the API. To build the documentation locally, run `make generate-api-spec`.

HTML-rendered API documentation can also be accessed within the running application at `http://localhost:8000/api/pattern-service/v1/docs/` or `http://localhost:8000/api/pattern-service/v1/docs/redoc/`
