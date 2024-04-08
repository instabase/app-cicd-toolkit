# 🤝 Contributing

Set of contribution guidelines for adding changes to the project

- [🤝 Contributing](#-contributing)
  - [🧪 Tests](#-tests)
    - [Setup](#setup)
    - [Running: Unit Tests](#running-unit-tests)

## 🧪 Tests

The project currently has a set of unit tests managed by [`pytest`](https://docs.pytest.org/) that can be run to test individual functionality of the code.

### Setup
The unit test environment relies on [`tox`](https://tox.wiki/en/4.12.0/) to produce a clean and isolated environment in each unit test run.
For guidelines on how to install and configure the `tox` CLI tool, [follow the installation instructions provided by the `tox` team](https://tox.wiki/en/4.12.0/installation.html).

### Running: Unit Tests

Once `tox` has been installed, the unit tests can be run by running

```bash
tox
```

within the project directory. This will handle generating a new virtual environment for the tests to run in, the project and test dependency installation,
followed by running the tests and any clean up that needs to be carried out.
